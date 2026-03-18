import re
from typing import List


def chunk_markdown_content(text: str, max_chars: int = 800, overlap: int = 100) -> List[str]:
    """
    Splits document text into semantic chunks.
    
    Strategy 1 (Markdown): splits on ## headers — works for LlamaParse output.
    Strategy 2 (Plain text): sliding window on sentence boundaries — works for PyPDF2 plain text.
    
    Args:
        text: Input text (markdown or plain)
        max_chars: Target max characters per chunk
        overlap: Characters of overlap between chunks (for context continuity)
    """
    text = text.strip()
    if not text:
        return []

    # --- Strategy 1: Markdown header-based splitting ---
    raw_chunks = re.split(r'(?=\n#{1,4}\s)', text)
    # Only use this path if we actually found headers (more than 1 block)
    if len(raw_chunks) > 1:
        chunks: List[str] = []
        current_chunk = ""
        for block in raw_chunks:
            block = block.strip()
            if not block:
                continue
            if len(current_chunk) + len(block) < max_chars:
                current_chunk += "\n\n" + block
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = block
        if current_chunk:
            chunks.append(current_chunk.strip())
        return [c for c in chunks if len(c) > 20]

    # --- Strategy 2: Sentence-boundary sliding window for plain text ---
    # Split on sentence endings (.!?) followed by whitespace/newline
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        if len(current_chunk) + len(sentence) + 1 <= max_chars:
            current_chunk = (current_chunk + " " + sentence).strip()
        else:
            if current_chunk:
                chunks.append(current_chunk)
            # Start new chunk with overlap from end of previous chunk
            if overlap > 0 and current_chunk:
                overlap_text = current_chunk[-overlap:].strip()
                current_chunk = (overlap_text + " " + sentence).strip()
            else:
                current_chunk = sentence

    if current_chunk:
        chunks.append(current_chunk)

    # Final safety: hard-split any remaining chunks still over max_chars
    final_chunks = []
    for chunk in chunks:
        if len(chunk) <= max_chars:
            final_chunks.append(chunk)
        else:
            for i in range(0, len(chunk), max_chars - overlap):
                piece = chunk[i:i + max_chars].strip()
                if piece:
                    final_chunks.append(piece)

    return [c for c in final_chunks if len(c) > 20]
