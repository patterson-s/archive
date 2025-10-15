# Writing Archive

Convert PhD documents into a searchable text archive.

## Setup

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload
```

Visit http://localhost:8000

## Current Features

- Upload PDF and DOCX files
- Parse to plain text with structure
- Preview and edit before saving
- Manual text entry

## Supported Formats

- PDF (.pdf)
- Word Documents (.docx)