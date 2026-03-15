from __future__ import annotations

from pathlib import Path

import fitz

from app.core.config import Settings
from app.models import DocumentIngestRequest
from app.services.parsing import FallbackParser, LlamaParseParser


def build_parser(tmp_path, **settings_overrides) -> LlamaParseParser:
    settings = Settings(data_dir=tmp_path / "data", qdrant_path=tmp_path / "qdrant", **settings_overrides)
    return LlamaParseParser(settings, fallback=FallbackParser(settings))


def test_chunk_page_entries_preserves_heading_bbox_and_order(tmp_path) -> None:
    parser = build_parser(tmp_path, llama_parse_api_key="test-key")
    blocks = parser._chunk_page_entries(
        1,
        [
            {
                "position": 1,
                "label": "section_header",
                "text": "Quarterly Results",
                "bbox": [10, 10, 120, 30],
                "ocr_confidence": 0.98,
                "source_type": "llamaparse_heading",
            },
            {
                "position": 2,
                "label": "body",
                "text": "Revenue reached 42 million USD in Q1.",
                "bbox": [10, 40, 220, 70],
                "ocr_confidence": 0.95,
                "source_type": "llamaparse_text",
            },
            {
                "position": 3,
                "label": "table",
                "text": "Table row 1: region = Europe; revenue = 42 million USD",
                "bbox": [10, 80, 260, 120],
                "ocr_confidence": None,
                "source_type": "llamaparse_table",
            },
        ],
    )

    assert len(blocks) == 2
    assert blocks[0].reading_order == 2
    assert blocks[0].bbox == [10, 40, 220, 70]
    assert blocks[0].text.startswith("Quarterly Results")
    assert blocks[1].source_type == "llamaparse_table"
    assert blocks[1].section == "table"


def test_fallback_parser_uses_native_pdf_text_for_pdf(tmp_path) -> None:
    settings = Settings(data_dir=tmp_path / "data", qdrant_path=tmp_path / "qdrant")
    parser = FallbackParser(settings)
    pdf_path = tmp_path / "native.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Level 4 process groups describe process elements in detail.")
    doc.save(pdf_path)
    doc.close()

    parsed = parser.parse(
        DocumentIngestRequest(
            source_path=str(pdf_path),
            filename=pdf_path.name,
            content_type="application/pdf",
        )
    )

    joined = " ".join(block.text for block in parsed.text_blocks)
    assert parsed.page_count == 1
    assert "Level 4 process groups" in joined
    assert parsed.image_regions


def test_llamaparse_parser_builds_page_chunks_and_images(tmp_path) -> None:
    parser = build_parser(tmp_path, llama_parse_api_key="test-key")
    pdf_path = tmp_path / "llamaparse.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "dummy")
    doc.save(pdf_path)
    doc.close()

    class StubClient:
        def get_json_result(self, source_path: str):
            assert source_path == str(pdf_path)
            return [
                {
                    "pages": [
                        {
                            "page": 1,
                            "width": 612,
                            "height": 792,
                            "confidence": 0.97,
                            "items": [
                                {
                                    "type": "heading",
                                    "value": "Level 4 - Activity",
                                    "bBox": {"x": 50, "y": 80, "w": 120, "h": 16, "confidence": 0.95},
                                },
                                {
                                    "type": "text",
                                    "value": "Indicates key events performed when executing a process.",
                                    "bBox": {"x": 50, "y": 104, "w": 420, "h": 20, "confidence": 0.93},
                                },
                            ],
                        }
                    ]
                }
            ]

    parser._llama_parse_client = StubClient()
    parsed = parser.parse(
        DocumentIngestRequest(
            source_path=str(pdf_path),
            filename=pdf_path.name,
            content_type="application/pdf",
        )
    )

    joined = " ".join(block.text for block in parsed.text_blocks)
    assert parsed.page_count == 1
    assert "Level 4 - Activity" in joined
    assert "Indicates key events performed" in joined
    assert parsed.image_regions
    assert parsed.ocr_metrics[0].engine == "llamaparse"


def test_llamaparse_parser_falls_back_when_remote_parse_fails(tmp_path) -> None:
    parser = build_parser(tmp_path, llama_parse_api_key="test-key")
    image_path = tmp_path / "page.png"
    image_path.write_bytes(b"PNG placeholder with dashboard text")

    class BrokenClient:
        def get_json_result(self, source_path: str):
            raise RuntimeError("nope")

    parser._llama_parse_client = BrokenClient()
    parsed = parser.parse(
        DocumentIngestRequest(
            source_path=str(image_path),
            filename=image_path.name,
            content_type="image/png",
        )
    )

    assert parsed.text_blocks
    assert parsed.image_regions
