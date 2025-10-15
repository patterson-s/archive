import sqlite3
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

ARCHIVE_DIR = Path("archive")
DB_PATH = ARCHIVE_DIR / "archive.db"

def init_database():
    ARCHIVE_DIR.mkdir(exist_ok=True)
    (ARCHIVE_DIR / "documents").mkdir(exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            original_type TEXT NOT NULL,
            file_size INTEGER,
            word_count INTEGER,
            created_date TEXT,
            added_date TEXT NOT NULL,
            md_path TEXT NOT NULL,
            notes TEXT
        )
    """)
    
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts 
        USING fts5(
            content,
            content=documents,
            content_rowid=id
        )
    """)
    
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS documents_ai 
        AFTER INSERT ON documents BEGIN
            INSERT INTO documents_fts(rowid, content)
            SELECT id, '' FROM documents WHERE id = new.id;
        END
    """)
    
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS documents_ad 
        AFTER DELETE ON documents BEGIN
            DELETE FROM documents_fts WHERE rowid = old.id;
        END
    """)
    
    conn.commit()
    conn.close()

def get_connection():
    return sqlite3.connect(DB_PATH)

def insert_document(
    filename: str,
    original_type: str,
    file_size: Optional[int],
    word_count: int,
    md_path: str,
    content: str,
    created_date: Optional[str] = None,
    notes: Optional[str] = None
) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    
    added_date = datetime.now().isoformat()
    
    cursor.execute("""
        INSERT INTO documents 
        (filename, original_type, file_size, word_count, created_date, added_date, md_path, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (filename, original_type, file_size, word_count, created_date, added_date, md_path, notes))
    
    doc_id = cursor.lastrowid
    
    cursor.execute("""
        INSERT INTO documents_fts(rowid, content)
        VALUES (?, ?)
    """, (doc_id, content))
    
    conn.commit()
    conn.close()
    
    return doc_id

def get_document(doc_id: int) -> Optional[Dict]:
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None

def search_documents(query: str, limit: int = 10):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT d.* 
        FROM documents d
        JOIN documents_fts fts ON d.id = fts.rowid
        WHERE documents_fts MATCH ?
        ORDER BY rank
        LIMIT ?
    """, (query, limit))
    
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return results

init_database()