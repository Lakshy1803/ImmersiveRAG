from __future__ import annotations

import mimetypes
import os
import re
from abc import ABC, abstractmethod
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

import fitz
import pdfplumber
from PIL import Image
from pypdf import PdfReader
from rapidocr import RapidOCR

from app.core.config import Settings
from app.core.warnings import silence_llama_index_pydantic_warning
from app.models import DocumentIngestRequest, ImageRegion, PageOcrMetrics, ParsedDocument, TextBlock

silence_llama_index_pydantic_warning()

from llama_index.core.node_parser import SentenceSplitter


TEXT_RE = re.compile(rb"[A-Za-z0-9][A-Za-z0-9 ,.:;()/%_-]{8,}")
BOUNDARY_RE = re.compile(r"(?<=[a-z])(?=[A-Z0-9])|(?<=[0-9])(?=[A-Za-z])")
WHITESPACE_RE = re.compile(r"\s+")
CURRENCY_RE = re.compile(r"([€£$₹])(?=\d)")
MAGNITUDE_RE = re.compile(r"(?<=\d)(million|billion|thousand|percent|usd|eur|inr|gbp)\b", re.IGNORECASE)
PDF_INTERNAL_RE = re.compile(
    r"(flatedecode|objstm|xobject|startxref|endstream|linearized|xmp\.|/catalog\b|/mediabox\b|/resources\b)",
    re.IGNORECASE,
)
LEVEL_RE = re.compile(r"^level\s+\d+\b", re.IGNORECASE)


class Parser(ABC):
    @abstractmethod
    def parse(self, request: DocumentIngestRequest) -> ParsedDocument:
        raise NotImplementedError


class FallbackParser(Parser):
    SUPPORTED_TYPES = {"application/pdf", "image/png", "image/jpeg", "image/jpg"}

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.settings.extracted_images_dir.mkdir(parents=True, exist_ok=True)
        self.splitter = SentenceSplitter(chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap)
        self._rapidocr_engine: RapidOCR | None = None

    def parse(self, request: DocumentIngestRequest) -> ParsedDocument:
        content_type = request.content_type or mimetypes.guess_type(request.filename)[0] or "application/octet-stream"
        if content_type not in self.SUPPORTED_TYPES:
            raise ValueError(f"Unsupported content type: {content_type}")
        if content_type == "application/pdf":
            pdf_document = self._parse_pdf_with_native_tools(request)
            if pdf_document is not None:
                return pdf_document

        source = Path(request.source_path)
        payload = source.read_bytes()
        text = self._extract_text(payload)
        text_blocks = self._chunk_text(text or f"Document content for {request.filename}")
        image_path = self._persist_image_preview(request.filename, 1, payload)
        image_regions = [
            ImageRegion(
                page_number=1,
                path=image_path,
                caption=(text.splitlines()[0] if text else f"Preview image extracted from {request.filename}")[:280],
                bbox=[0, 0, 1000, 1000],
            )
        ]
        self._write_caption_sidecar(image_path, image_regions[0].caption)
        return ParsedDocument(
            filename=request.filename,
            content_type=request.content_type,
            tenant_id=request.tenant_id,
            collection_id=request.collection_id,
            metadata=request.metadata,
            text_blocks=text_blocks,
            image_regions=image_regions,
            page_count=1,
            source_path=request.source_path,
        )

    def _parse_pdf_with_native_tools(self, request: DocumentIngestRequest) -> ParsedDocument | None:
        source = Path(request.source_path)
        try:
            with pdfplumber.open(source) as pdf:
                if not pdf.pages:
                    return None
                text_blocks: list[TextBlock] = []
                image_regions: list[ImageRegion] = []
                ocr_metrics: list[PageOcrMetrics] = []
                page_text_map: dict[int, list[str]] = defaultdict(list)
                for index, page in enumerate(pdf.pages, start=1):
                    page_blocks = self._pdf_page_text_blocks(page, index)
                    table_blocks = self._pdf_page_table_blocks(page, index)
                    ocr_blocks: list[TextBlock] = []
                    if page_blocks:
                        text_blocks.extend(page_blocks)
                    if table_blocks:
                        text_blocks.extend(table_blocks)
                    image_path = self._render_pdf_page_image(source, request.filename, index)
                    if self._should_ocr_rendered_pdf_page(page_blocks, table_blocks):
                        ocr_blocks = self._pdf_page_ocr_blocks(Path(image_path), index)
                        if ocr_blocks:
                            text_blocks.extend(ocr_blocks)
                    for block in [*page_blocks, *table_blocks, *ocr_blocks]:
                        if block.text not in page_text_map[index]:
                            page_text_map[index].append(block.text)
                    caption = self._pdf_caption_for_page(index, page_text_map, request.filename)
                    self._write_caption_sidecar(image_path, caption)
                    image_regions.append(
                        ImageRegion(
                            page_number=index,
                            path=image_path,
                            caption=caption,
                            bbox=[0, 0, int(page.width), int(page.height)],
                        )
                    )
                    page_confidence = self._pdf_native_text_confidence(page_blocks, table_blocks, ocr_blocks)
                    ocr_metrics.append(
                        PageOcrMetrics(
                            page_number=index,
                            engine="native_pdf+ocr" if ocr_blocks else "native_pdf",
                            average_confidence=page_confidence,
                            min_confidence=page_confidence,
                            max_confidence=page_confidence,
                            text_cell_count=len(page_blocks) + len(table_blocks) + len(ocr_blocks),
                            low_confidence_cells=0 if page_confidence is not None else 1,
                        )
                    )
        except Exception:
            return None

        if not text_blocks:
            return None
        joined = " ".join(block.text for block in text_blocks[:10])
        if self._looks_like_pdf_internal_text(joined):
            return None
        return ParsedDocument(
            filename=request.filename,
            content_type=request.content_type,
            tenant_id=request.tenant_id,
            collection_id=request.collection_id,
            metadata=request.metadata,
            text_blocks=text_blocks,
            image_regions=image_regions,
            ocr_metrics=ocr_metrics,
            page_count=max((region.page_number for region in image_regions), default=1),
            source_path=request.source_path,
        )

    def _extract_text(self, payload: bytes) -> str:
        candidates = [match.decode("utf-8", errors="ignore").strip() for match in TEXT_RE.findall(payload)]
        return "\n".join(dict.fromkeys(candidate for candidate in candidates if candidate))

    def _persist_image_preview(self, filename: str, page_number: int, payload: bytes) -> str:
        target = self.settings.extracted_images_dir / f"{Path(filename).stem}_page_{page_number}.bin"
        target.write_bytes(payload)
        return str(target)

    def _write_caption_sidecar(self, image_path: str, caption: str) -> None:
        Path(image_path + ".caption.txt").write_text(caption, encoding="utf-8")

    def _chunk_text(self, text: str, page_number: int = 1, section: str = "body") -> list[TextBlock]:
        cleaned = " ".join(text.split())
        if not cleaned:
            return []
        return [TextBlock(page_number=page_number, section=section, text=chunk) for chunk in self.splitter.split_text(cleaned)]

    def _pdf_caption_for_page(self, page_number: int, page_text_map: dict[int, list[str]], filename: str) -> str:
        snippets = page_text_map.get(page_number, [])[:2]
        if not snippets:
            return f"Page {page_number} extracted from {filename}"[:280]
        return " ".join(snippets)[:280]

    def _pdf_native_text_confidence(
        self,
        page_blocks: list[TextBlock],
        table_blocks: list[TextBlock],
        ocr_blocks: list[TextBlock],
    ) -> float | None:
        scores = [block.ocr_confidence for block in [*page_blocks, *table_blocks, *ocr_blocks] if block.ocr_confidence is not None]
        return mean(scores) if scores else None

    def _pdf_page_text_blocks(self, page, page_number: int) -> list[TextBlock]:
        try:
            lines = page.extract_text_lines(layout=False, return_chars=False)
        except Exception:
            lines = []
        if not lines:
            text = self._normalize_text(page.extract_text() or "")
            return self._chunk_text(text, page_number=page_number) if text else []

        blocks: list[TextBlock] = []
        buffer_lines: list[dict[str, Any]] = []

        def flush(section: str = "body") -> None:
            nonlocal buffer_lines
            if not buffer_lines:
                return
            joined = " ".join(self._normalize_text(str(line["text"])) for line in buffer_lines if str(line["text"]).strip())
            joined = self._normalize_text(joined)
            if not joined:
                buffer_lines = []
                return
            bbox = [
                int(min(float(line["x0"]) for line in buffer_lines)),
                int(min(float(line["top"]) for line in buffer_lines)),
                int(max(float(line["x1"]) for line in buffer_lines)),
                int(max(float(line["bottom"]) for line in buffer_lines)),
            ]
            for chunk in self._chunk_text(joined, page_number=page_number, section=section):
                chunk.bbox = bbox
                chunk.reading_order = len(blocks)
                chunk.ocr_confidence = 1.0
                chunk.source_type = "native_pdf_text"
                blocks.append(chunk)
            buffer_lines = []

        previous_top: float | None = None
        for line in sorted(lines, key=lambda item: (float(item["top"]), float(item["x0"]))):
            raw_text = str(line.get("text", "")).strip()
            if not raw_text:
                continue
            normalized = self._normalize_text(raw_text)
            if not normalized:
                continue
            is_heading = len(normalized) <= 120 and normalized.upper() == normalized and any(ch.isalpha() for ch in normalized)
            current_top = float(line["top"])
            gap = (current_top - previous_top) if previous_top is not None else 0.0
            if is_heading:
                flush()
                buffer_lines = [line]
                flush()
                previous_top = current_top
                continue
            if buffer_lines and gap > 18:
                flush()
            buffer_lines.append(line)
            previous_top = current_top
        flush()
        return blocks

    def _pdf_page_table_blocks(self, page, page_number: int) -> list[TextBlock]:
        blocks: list[TextBlock] = []
        try:
            tables = page.extract_tables() or []
        except Exception:
            tables = []
        for table_index, table in enumerate(tables, start=1):
            for row_index, row in enumerate(table[:8], start=1):
                cleaned = []
                for col_index, value in enumerate(row or [], start=1):
                    text = self._normalize_text("" if value is None else str(value))
                    if text:
                        cleaned.append(f"c{col_index} = {text}")
                if cleaned:
                    blocks.append(
                        TextBlock(
                            page_number=page_number,
                            section="table",
                            text=f"Table {table_index} row {row_index}: {'; '.join(cleaned)}",
                            reading_order=10000 + table_index * 100 + row_index,
                            ocr_confidence=1.0,
                            source_type="native_pdf_table",
                        )
                    )
        return blocks

    def _render_pdf_page_image(self, source: Path, filename: str, page_number: int) -> str:
        doc = fitz.open(source)
        try:
            page = doc.load_page(page_number - 1)
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
            target = self.settings.extracted_images_dir / f"{Path(filename).stem}_page_{page_number}.png"
            pixmap.save(target)
            return str(target)
        finally:
            doc.close()

    def _normalize_text(self, text: str) -> str:
        normalized = text.replace("\x00", " ").replace("\n", " ")
        normalized = CURRENCY_RE.sub(r"\1 ", normalized)
        normalized = BOUNDARY_RE.sub(" ", normalized)
        normalized = MAGNITUDE_RE.sub(r" \1", normalized)
        normalized = WHITESPACE_RE.sub(" ", normalized)
        return normalized.strip()

    def _looks_like_pdf_internal_text(self, text: str) -> bool:
        cleaned = " ".join(text.split())
        if not cleaned:
            return True
        if PDF_INTERNAL_RE.search(cleaned):
            return True
        alpha_chars = sum(1 for ch in cleaned if ch.isalpha())
        if alpha_chars < 25:
            return True
        suspicious_tokens = {"obj", "endobj", "xref", "startxref", "stream", "endstream", "mediabox"}
        token_count = sum(1 for token in cleaned.lower().split() if token in suspicious_tokens)
        return token_count >= 2

    def _should_ocr_rendered_pdf_page(self, page_blocks: list[TextBlock], table_blocks: list[TextBlock]) -> bool:
        combined = " ".join(block.text for block in [*page_blocks, *table_blocks])
        return len(page_blocks) <= 4 or len(combined) < 260

    def _pdf_page_ocr_blocks(self, image_path: Path, page_number: int) -> list[TextBlock]:
        engine = self._get_rapidocr_engine()
        output = engine(image_path, text_score=self.settings.llama_parse_confidence_threshold)
        raw_boxes = getattr(output, "boxes", None)
        raw_texts = getattr(output, "txts", None)
        raw_scores = getattr(output, "scores", None)
        boxes = list(raw_boxes) if raw_boxes is not None else []
        texts = list(raw_texts) if raw_texts is not None else []
        scores = list(raw_scores) if raw_scores is not None else []
        entries: list[dict[str, Any]] = []
        for order, text in enumerate(texts):
            normalized = self._normalize_text(str(text))
            if not normalized or len(normalized) < 4:
                continue
            bbox = None
            if order < len(boxes):
                box = boxes[order]
                xs = [point[0] for point in box]
                ys = [point[1] for point in box]
                bbox = [int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))]
            score = float(scores[order]) if order < len(scores) else None
            entries.append(
                {
                    "text": normalized,
                    "bbox": bbox,
                    "score": score,
                    "order": 20000 + order,
                    "is_level_heading": bool(LEVEL_RE.match(normalized)),
                    "is_heading": normalized.upper() == normalized,
                }
            )
        return self._group_pdf_ocr_entries(entries, page_number)

    def _get_rapidocr_engine(self) -> RapidOCR:
        if self._rapidocr_engine is None:
            self._rapidocr_engine = RapidOCR()
        return self._rapidocr_engine

    def _group_pdf_ocr_entries(self, entries: list[dict[str, Any]], page_number: int) -> list[TextBlock]:
        blocks: list[TextBlock] = []
        buffer: list[dict[str, Any]] = []

        def flush() -> None:
            nonlocal buffer
            if not buffer:
                return
            text = " ".join(item["text"] for item in buffer)
            bboxes = [item["bbox"] for item in buffer if item["bbox"]]
            bbox = None
            if bboxes:
                bbox = [
                    min(item[0] for item in bboxes),
                    min(item[1] for item in bboxes),
                    max(item[2] for item in bboxes),
                    max(item[3] for item in bboxes),
                ]
            scores = [item["score"] for item in buffer if item["score"] is not None]
            blocks.append(
                TextBlock(
                    page_number=page_number,
                    section="body",
                    text=text,
                    bbox=bbox,
                    reading_order=buffer[0]["order"],
                    ocr_confidence=(sum(scores) / len(scores)) if scores else None,
                    source_type="rendered_pdf_ocr",
                )
            )
            buffer = []

        for entry in sorted(entries, key=lambda item: item["order"]):
            if entry["is_level_heading"]:
                flush()
                buffer = [entry]
                continue
            if buffer and (entry["is_heading"] or entry["order"] - buffer[-1]["order"] > 3):
                flush()
            buffer.append(entry)
        flush()
        return blocks


class LlamaParseParser(Parser):
    HEADING_LABELS = {"title", "section_header", "header"}

    def __init__(self, settings: Settings, fallback: Parser | None = None) -> None:
        self.settings = settings
        self.fallback = fallback or FallbackParser(settings)
        self.settings.extracted_images_dir.mkdir(parents=True, exist_ok=True)
        self.splitter = SentenceSplitter(chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap)
        self._llama_parse_client = None

    def parse(self, request: DocumentIngestRequest) -> ParsedDocument:
        try:
            return self._parse_with_llamaparse(request)
        except Exception:
            return self.fallback.parse(request)

    def _parse_with_llamaparse(self, request: DocumentIngestRequest) -> ParsedDocument:
        client = self._get_llamaparse_client()
        source = Path(request.source_path)
        payload = client.get_json_result(str(source))
        document = payload[0] if isinstance(payload, list) else payload
        pages = list(document.get("pages") or [])
        if not pages:
            raise ValueError("LlamaParse returned no pages")

        text_blocks: list[TextBlock] = []
        image_regions: list[ImageRegion] = []
        ocr_metrics: list[PageOcrMetrics] = []
        page_text_map: dict[int, list[str]] = defaultdict(list)
        for page in pages:
            page_number = int(page.get("page") or len(image_regions) + 1)
            page_entries = self._llamaparse_entries_from_page(page)
            page_blocks = self._chunk_page_entries(page_number, page_entries)
            if not page_blocks:
                fallback_text = self._normalize_text(str(page.get("md") or page.get("text") or ""))
                page_blocks = self.fallback._chunk_text(fallback_text, page_number=page_number) if fallback_text else []
                for block in page_blocks:
                    block.source_type = "llamaparse_page"
            text_blocks.extend(page_blocks)
            for block in page_blocks:
                if block.text not in page_text_map[page_number]:
                    page_text_map[page_number].append(block.text)

            image_path = self._persist_page_image(source, request.filename, page_number)
            caption = self._caption_for_page(page_number, page_text_map, request.filename)
            Path(image_path + ".caption.txt").write_text(caption, encoding="utf-8")
            width = int(page.get("width") or 0)
            height = int(page.get("height") or 0)
            image_regions.append(
                ImageRegion(
                    page_number=page_number,
                    path=image_path,
                    caption=caption,
                    bbox=[0, 0, width, height],
                )
            )
            page_confidence = float(page.get("confidence") or 0.0) or None
            ocr_metrics.append(
                PageOcrMetrics(
                    page_number=page_number,
                    engine="llamaparse",
                    average_confidence=page_confidence,
                    min_confidence=page_confidence,
                    max_confidence=page_confidence,
                    text_cell_count=len(page_entries),
                    low_confidence_cells=0 if page_confidence is None or page_confidence >= self.settings.llama_parse_confidence_threshold else 1,
                )
            )

        if not text_blocks:
            raise ValueError("LlamaParse returned no text blocks")

        return ParsedDocument(
            filename=request.filename,
            content_type=request.content_type,
            tenant_id=request.tenant_id,
            collection_id=request.collection_id,
            metadata=request.metadata,
            text_blocks=text_blocks,
            image_regions=image_regions,
            ocr_metrics=ocr_metrics,
            page_count=len(pages),
            source_path=request.source_path,
        )

    def _get_llamaparse_client(self):
        if self._llama_parse_client is not None:
            return self._llama_parse_client
        api_key = self.settings.llama_parse_api_key or os.getenv("LLAMA_CLOUD_API_KEY")
        if not api_key:
            raise ValueError("missing llama parse api key")
        from llama_parse import LlamaParse

        self._llama_parse_client = LlamaParse(
            api_key=api_key,
            result_type=self.settings.llama_parse_result_type,
            split_by_page=True,
            extract_layout=True,
            disable_image_extraction=False,
            language=self.settings.llama_parse_language,
            num_workers=self.settings.llama_parse_num_workers,
            fast_mode=self.settings.llama_parse_fast_mode,
            premium_mode=self.settings.llama_parse_premium_mode,
            verbose=self.settings.llama_parse_verbose,
            disable_ocr=not self.settings.llama_parse_do_ocr,
        )
        return self._llama_parse_client

    def _llamaparse_entries_from_page(self, page: dict[str, Any]) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        raw_items = page.get("items") or []
        if not isinstance(raw_items, list):
            raw_items = []
        for position, item in enumerate(raw_items):
            text = self._normalize_text(str(item.get("value") or item.get("md") or item.get("text") or ""))
            if not text:
                continue
            item_type = str(item.get("type") or "text").lower()
            entries.append(
                {
                    "position": position,
                    "label": self._llamaparse_label(item_type, text),
                    "text": text,
                    "bbox": self._llamaparse_bbox(item.get("bBox")),
                    "ocr_confidence": self._llamaparse_confidence(item.get("bBox"), page.get("confidence")),
                    "source_type": f"llamaparse_{item_type}",
                }
            )
        return entries

    def _llamaparse_label(self, item_type: str, text: str) -> str:
        if item_type in {"heading", "header", "title"}:
            return "section_header"
        if item_type == "table":
            return "table"
        if item_type in {"caption", "footnote"}:
            return "caption"
        if item_type in {"list", "list_item", "bullet"} or text.lstrip().startswith(("-", "*", "\u2022")):
            return "list"
        if len(text) <= 120 and text.upper() == text and any(ch.isalpha() for ch in text):
            return "section_header"
        return "body"

    def _llamaparse_bbox(self, bbox: Any) -> list[int] | None:
        if not isinstance(bbox, dict):
            return None
        x = float(bbox.get("x") or 0.0)
        y = float(bbox.get("y") or 0.0)
        w = float(bbox.get("w") or 0.0)
        h = float(bbox.get("h") or 0.0)
        return [int(x), int(y), int(x + w), int(y + h)]

    def _llamaparse_confidence(self, bbox: Any, page_confidence: Any) -> float | None:
        if isinstance(bbox, dict) and bbox.get("confidence") is not None:
            return float(bbox["confidence"])
        if page_confidence is not None:
            return float(page_confidence)
        return None

    def _persist_page_image(self, source: Path, filename: str, page_number: int) -> str:
        content_type = mimetypes.guess_type(source.name)[0] or ""
        if content_type.startswith("image/"):
            suffix = source.suffix.lower() or ".bin"
            target = self.settings.extracted_images_dir / f"{Path(filename).stem}_page_{page_number}{suffix}"
            if source.resolve() != target.resolve():
                target.write_bytes(source.read_bytes())
            return str(target)

        doc = fitz.open(source)
        try:
            page = doc.load_page(page_number - 1)
            pixmap = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
            target = self.settings.extracted_images_dir / f"{Path(filename).stem}_page_{page_number}.png"
            pixmap.save(target)
            return str(target)
        finally:
            doc.close()

    def _caption_for_page(self, page_number: int, page_text_map: dict[int, list[str]], filename: str) -> str:
        snippets = page_text_map.get(page_number, [])[:2]
        if not snippets:
            return f"Page {page_number} extracted from {filename}"[:280]
        return " ".join(snippets)[:280]

    def _chunk_page_entries(self, page_number: int, entries: list[dict[str, Any]]) -> list[TextBlock]:
        blocks: list[TextBlock] = []
        current_heading: str | None = None
        current_section = "body"
        buffer: list[dict[str, Any]] = []

        def flush() -> None:
            nonlocal buffer
            if not buffer:
                return
            prefix = f"{current_heading}\n" if current_heading and current_section != "table" else ""
            chunk_source = prefix + "\n".join(entry["text"] for entry in buffer)
            chunk_source = self._normalize_text(chunk_source)
            if not chunk_source:
                buffer = []
                return
            chunk_bbox = self._merge_bboxes(entry["bbox"] for entry in buffer)
            chunk_order = buffer[0]["position"]
            ocr_confidences = [entry["ocr_confidence"] for entry in buffer if entry["ocr_confidence"] is not None]
            source_types = {entry["source_type"] for entry in buffer}
            for chunk in self.splitter.split_text(chunk_source):
                blocks.append(
                    TextBlock(
                        page_number=page_number,
                        section=current_section,
                        text=chunk,
                        bbox=chunk_bbox,
                        reading_order=chunk_order,
                        ocr_confidence=(sum(ocr_confidences) / len(ocr_confidences)) if ocr_confidences else None,
                        source_type=next(iter(source_types)) if len(source_types) == 1 else "mixed",
                    )
                )
            buffer = []

        for entry in entries:
            label = entry["label"]
            if label == "section_header":
                flush()
                current_heading = entry["text"]
                current_section = "body"
                continue
            if label == "table":
                flush()
                current_section = "table"
                buffer = [entry]
                flush()
                current_section = "body"
                continue
            if label in {"caption", "list"} and buffer:
                flush()
            buffer.append(entry)
        flush()
        return blocks

    def _merge_bboxes(self, bboxes) -> list[int] | None:
        cleaned = [bbox for bbox in bboxes if bbox]
        if not cleaned:
            return None
        return [
            min(bbox[0] for bbox in cleaned),
            min(bbox[1] for bbox in cleaned),
            max(bbox[2] for bbox in cleaned),
            max(bbox[3] for bbox in cleaned),
        ]

    def _normalize_text(self, text: str) -> str:
        normalized = text.replace("\x00", " ").replace("\n", " ")
        normalized = CURRENCY_RE.sub(r"\1 ", normalized)
        normalized = BOUNDARY_RE.sub(" ", normalized)
        normalized = MAGNITUDE_RE.sub(r" \1", normalized)
        normalized = WHITESPACE_RE.sub(" ", normalized)
        return normalized.strip()
