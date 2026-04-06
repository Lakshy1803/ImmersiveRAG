import logging

logger = logging.getLogger(__name__)


def _int_color_to_hex(color_int: int) -> str:
    """Convert PyMuPDF integer color to hex string."""
    r = (color_int >> 16) & 0xFF
    g = (color_int >> 8) & 0xFF
    b = color_int & 0xFF
    return f"#{r:02x}{g:02x}{b:02x}"


def _is_near_black_or_white(hex_color: str) -> bool:
    """Detect if color is too dark/light to be a brand accent."""
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    brightness = (r * 299 + g * 587 + b * 114) / 1000
    # Reject very dark (<40) and very light (>215)
    return brightness < 40 or brightness > 215


def extract_style_from_pdf(pdf_bytes: bytes) -> dict:
    """
    Analyzes the first 3 pages of a PDF to extract brand colors, font info,
    and a markdown skeleton of the document structure (headings).

    Returns a dict with keys:
        - primary_color    (most frequent non-neutral color)
        - secondary_color  (second most frequent)
        - font_family      (CSS-safe family string)
        - markdown_skeleton (heading hierarchy as markdown, e.g. "# Title\n## Section\n...")
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.error("PyMuPDF not installed. Cannot extract PDF style.")
        return _default_style()

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        logger.error(f"Failed to open PDF stream: {e}")
        return _default_style()

    color_counts: dict[str, int] = {}
    font_counts: dict[str, int] = {}

    # For skeleton extraction: collect all spans with size info across all pages
    all_spans: list[dict] = []

    pages_to_scan = min(3, len(doc))
    for page_idx in range(pages_to_scan):
        try:
            page = doc[page_idx]
            data = page.get_text("dict")
            for block in data.get("blocks", []):
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if not text:
                            continue

                        char_count = len(text)
                        color_int = span.get("color", 0)
                        hex_col = _int_color_to_hex(color_int)

                        if not _is_near_black_or_white(hex_col):
                            color_counts[hex_col] = color_counts.get(hex_col, 0) + char_count

                        raw_font = span.get("font", "")
                        font_name = raw_font.split("+")[-1] if "+" in raw_font else raw_font
                        if font_name:
                            font_counts[font_name] = font_counts.get(font_name, 0) + char_count

                        all_spans.append({
                            "text":  text,
                            "size":  span.get("size", 12),
                            "flags": span.get("flags", 0),  # bold = flags & 16
                        })
        except Exception as e:
            logger.warning(f"Error scanning page {page_idx}: {e}")
            continue

    # Sort colors by frequency
    sorted_colors = sorted(color_counts.items(), key=lambda x: x[1], reverse=True)
    primary   = sorted_colors[0][0] if len(sorted_colors) > 0 else "#EB8C00"
    secondary = sorted_colors[1][0] if len(sorted_colors) > 1 else "#E0301E"

    # Map detected font to xhtml2pdf-safe font stack
    top_font = sorted(font_counts.items(), key=lambda x: x[1], reverse=True)
    font_family = _resolve_font_family(top_font[0][0] if top_font else "")

    # --- Build Markdown Skeleton ---
    skeleton = _build_markdown_skeleton(all_spans)

    return {
        "primary_color":     primary,
        "secondary_color":   secondary,
        "font_family":       font_family,
        "markdown_skeleton": skeleton,
    }


def _build_markdown_skeleton(spans: list[dict]) -> str:
    """
    Infer document headings from font size and boldness, and produce a
    markdown skeleton with # / ## / ### markers.
    """
    if not spans:
        return ""

    # Determine sizing thresholds from the actual document
    sizes = sorted(set(round(s["size"]) for s in spans), reverse=True)
    body_size = sizes[-1] if sizes else 12

    # Only treat text significantly larger than body as headings
    heading_sizes = [s for s in sizes if s > body_size + 2]
    if not heading_sizes:
        # Fallback: just return a generic skeleton
        return "# Document Title\n\n## Section 1\n\n## Section 2\n\n## References"

    # Map the top-3 distinct sizes to heading levels
    size_to_level: dict[int, int] = {}
    for i, s in enumerate(heading_sizes[:3]):
        size_to_level[s] = i + 1  # 1 = H1, 2 = H2, 3 = H3

    seen: list[str] = []
    skeleton_lines: list[str] = []

    for span in spans:
        sz = round(span["size"])
        is_bold = bool(span["flags"] & 16)
        text = span["text"].strip()

        # A heading candidate: large font OR bold
        if sz in size_to_level or (is_bold and sz > body_size):
            level = size_to_level.get(sz, 2)
            heading_md = f"{'#' * level} {text}"
            # Deduplicate consecutive identical lines
            if not seen or seen[-1] != heading_md:
                seen.append(heading_md)
                skeleton_lines.append(heading_md)
                skeleton_lines.append("")  # blank line after each heading

    if not skeleton_lines:
        return "# Document Title\n\n## Section 1\n\n## Section 2\n\n## References"

    return "\n".join(skeleton_lines).strip()


def _resolve_font_family(raw_font: str) -> str:
    """Map detected font name to a pisa-compatible font-family string."""
    lower = raw_font.lower()
    if "times" in lower or "serif" in lower:
        return "Times, serif"
    if "courier" in lower or "mono" in lower:
        return "Courier, monospace"
    return "Helvetica, Arial, sans-serif"


def _default_style() -> dict:
    return {
        "primary_color":     "#EB8C00",
        "secondary_color":   "#E0301E",
        "font_family":       "Helvetica, Arial, sans-serif",
        "markdown_skeleton": "# Document Title\n\n## Section 1\n\n## Section 2\n\n## References",
    }

