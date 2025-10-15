import pdfplumber
from typing import Dict

def parse_pdf(file_path: str) -> Dict[str, str]:
    text_parts = []
    num_pages = 0
    
    with pdfplumber.open(file_path) as pdf:
        num_pages = len(pdf.pages)
        for page in pdf.pages:
            text = page.extract_text()
            if text and text.strip():
                text_parts.append(text.strip())
    
    full_text = "\n\n".join(text_parts)
    
    metadata = {
        "num_pages": num_pages,
        "content": full_text
    }
    
    return metadata