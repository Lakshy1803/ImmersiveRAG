import logging
from app.core.config import config
import os

try:
    import pytesseract
    HAS_PYTESSERACT = True
except ImportError:
    HAS_PYTESSERACT = False

try:
    import easyocr
    HAS_EASYOCR = True
except ImportError:
    HAS_EASYOCR = False

logger = logging.getLogger(__name__)

# Configure pytesseract path if provided
if HAS_PYTESSERACT and config.tesseract_cmd_path:
    # Resolve relative paths gracefully from backend root
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    tess_path = config.tesseract_cmd_path
    if not os.path.isabs(tess_path):
        tess_path = os.path.join(base_path, tess_path)
    
    if os.path.exists(tess_path):
        pytesseract.pytesseract.tesseract_cmd = tess_path
        logger.info(f"Tesseract mapped to: {tess_path}")
    else:
        logger.warning(f"Configured Tesseract path not found: {tess_path}")

# Initialize EasyOCR reader lazily to avoid heavy load on startup
_reader = None

def get_easyocr_reader():
    global _reader
    if _reader is None and HAS_EASYOCR:
        logger.info("Initializing EasyOCR reader (CPU mode fallback).")
        _reader = easyocr.Reader(['en'], gpu=False) # Adjust GPU flag if CUDA available
    return _reader

def extract_text_from_image(image_path: str, use_easyocr: bool = False) -> str:
    """Extracts text from a PNG/image file using either EasyOCR or Tesseract."""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
        
    try:
        if use_easyocr and HAS_EASYOCR:
            logger.info(f"Extracting text using EasyOCR for {image_path}")
            reader = get_easyocr_reader()
            results = reader.readtext(image_path)
            return "\n".join([text for (_, text, _) in results])
        elif HAS_PYTESSERACT:
            logger.info(f"Extracting text using Tesseract for {image_path}")
            return pytesseract.image_to_string(image_path)
        else:
            logger.error("Neither PyTesseract nor EasyOCR is installed.")
            return "OCR dependencies missing. Install pytesseract or easyocr."
            
    except Exception as e:
        logger.error(f"OCR Extraction failed: {e}")
        return f"[OCR Extraction Failed: {str(e)}]"

def extract_text_from_pdf_locally(pdf_path: str, use_easyocr: bool = False) -> list[dict]:
    """Extracts text from a PDF. If it's a scanned PDF (no text), it converts the page to an image and runs OCR."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.error("PyMuPDF not installed. Cannot process local PDFs.")
        return [{"text": "Error: PyMuPDF is missing. Run `pip install pymupdf`", "metadata": {"page": "1"}}]
        
    import tempfile
    
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    doc = fitz.open(pdf_path)
    pages_data = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # 1. Try extracting standard digital text
        text = page.get_text()
        
        # 2. If no meaningful text was found, we assume it's a scanned page and OCR it
        if len(text.strip()) < 50:
            logger.info(f"Page {page_num + 1} seems to be scanned. Running OCR on image extraction...")
            pix = page.get_pixmap(dpi=150)
            
            # Create temp file but explicitly close it so Windows releases the lock
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            tmp_path = tmp.name
            tmp.close()
            
            try:
                pix.save(tmp_path)
                ocr_text = extract_text_from_image(tmp_path, use_easyocr=use_easyocr)
                if ocr_text and not ocr_text.startswith("[OCR Extraction Failed"):
                    text = ocr_text
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                    
        pages_data.append({
            "text": text,
            "metadata": {"page": str(page_num + 1), "type": "pdf_local"}
        })
        
    return pages_data

