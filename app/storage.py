from pathlib import Path
from datetime import datetime
import re
from typing import Optional

from app.database import insert_document, ARCHIVE_DIR

def calculate_word_count(text: str) -> int:
    words = re.findall(r'\b\w+\b', text)
    return len(words)

def generate_md_filename(original_filename: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = Path(original_filename).stem
    safe_name = re.sub(r'[^\w\s-]', '', base_name)
    safe_name = re.sub(r'[-\s]+', '_', safe_name)
    return f"{timestamp}_{safe_name}.md"

def save_document(
    filename: str,
    original_type: str,
    content: str,
    file_size: Optional[int] = None,
    created_date: Optional[str] = None,
    notes: Optional[str] = None
) -> int:
    documents_dir = ARCHIVE_DIR / "documents"
    documents_dir.mkdir(parents=True, exist_ok=True)
    
    md_filename = generate_md_filename(filename)
    md_path = documents_dir / md_filename
    
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    word_count = calculate_word_count(content)
    
    doc_id = insert_document(
        filename=filename,
        original_type=original_type,
        file_size=file_size,
        word_count=word_count,
        md_path=str(md_path),
        content=content,
        created_date=created_date,
        notes=notes
    )
    
    return doc_id