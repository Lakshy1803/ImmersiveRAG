import re
from typing import List, Dict

def chunk_markdown_content(pages: List[dict], filename: str, max_chars: int = 800, overlap: int = 100) -> List[dict]:
    """
    Splits document pages into semantic chunks while maintaining metadata.
    
    Args:
        pages: List of mapped pages like {"text": "...", "metadata": {"page": "1"}}
        filename: Name of the uploaded file
        max_chars: Target max characters per chunk
        overlap: Characters of overlap between chunks
    """
    chunks = []
    current_heading = "Unknown Heading"
    
    for page in pages:
        text = page.get("text", "").strip()
        if not text:
            continue
            
        page_num = page.get("metadata", {}).get("page", "1")
        
        # Split text on markdown headers to track sectional context
        raw_blocks = re.split(r'(?=\n#{1,4}\s)', "\n" + text)
        
        for block in raw_blocks:
            block = block.strip()
            if not block:
                continue
                
            # Check if this block starts with a header, update context if so
            header_match = re.match(r'^(#{1,4})\s+(.+?)(?:\n|$)', block)
            if header_match:
                current_heading = header_match.group(2).strip()
                
            # Chunk the block sequentially (combining paragraphs/sentences)
            sentences = re.split(r'(?<=[.!?])\s+', block)
            current_chunk = ""
            
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence: continue
                
                if len(current_chunk) + len(sentence) + 1 <= max_chars:
                    current_chunk = (current_chunk + " " + sentence).strip()
                else:
                    if current_chunk:
                        chunks.append({
                            "text": current_chunk,
                            "metadata": {
                                "file_name": filename,
                                "page_label": str(page_num),
                                "heading": current_heading
                            }
                        })
                    if overlap > 0 and current_chunk:
                        overlap_text = current_chunk[-overlap:].strip()
                        current_chunk = (overlap_text + " " + sentence).strip()
                    else:
                        current_chunk = sentence
                        
            if current_chunk:
                chunks.append({
                    "text": current_chunk,
                    "metadata": {
                        "file_name": filename,
                        "page_label": str(page_num),
                        "heading": current_heading
                    }
                })

    # Final safety: hard-split chunks that are still over max_chars
    final_chunks = []
    for chunk in chunks:
        c_text = chunk["text"]
        if len(c_text) <= max_chars:
            final_chunks.append(chunk)
        else:
            for i in range(0, len(c_text), max_chars - overlap):
                piece = c_text[i:i + max_chars].strip()
                if piece:
                    # clone metadata for piece
                    final_chunks.append({
                        "text": piece,
                        "metadata": chunk["metadata"].copy()
                    })

    # Drop very tiny residual chunks
    return [c for c in final_chunks if len(c["text"]) > 20]
