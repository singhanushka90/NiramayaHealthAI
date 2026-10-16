import fitz
import pytesseract

from PIL import Image
from io import BytesIO

def extract_text_with_ocr(file_path:str)->dict:
    """Extract text from scanned PDF pages using Tesseract OCS"""
    extracted_pages=[]
    with fitz.open(file_path) as document:
        for page_number,page in enumerate(document,start=1):
            pixmap=page.get_pixmap(matrix=fitz.Matrix(2,2),alpha=False)

            image=Image.open(BytesIO(pixmap.tobytes("png")))
            text=pytesseract.image_to_string(image,lang="eng")
            extracted_pages.append({"page_number":page_number,"text":text.strip})
    full_text="\n\n".join(page["text"] for page in extracted_pages)
    return {
        "text":full_text,
        "total_pages":len(extracted_pages),
        "text_length":len(full_text),
        "pages":extracted_pages
    }        
