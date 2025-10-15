from fastapi import FastAPI, UploadFile, File, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import tempfile
from pathlib import Path

from app.parsers.pdf import parse_pdf
from app.parsers.docx import parse_docx

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

SUPPORTED_TYPES = {
    ".pdf": parse_pdf,
    ".docx": parse_docx,
}

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_ext = Path(file.filename).suffix.lower()
    
    if file_ext not in SUPPORTED_TYPES:
        return JSONResponse(
            status_code=400,
            content={"error": f"Unsupported file type: {file_ext}"}
        )
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        parser = SUPPORTED_TYPES[file_ext]
        parsed_data = parser(tmp_path)
        
        response = {
            "filename": file.filename,
            "file_type": file_ext,
            "content": parsed_data["content"],
            "metadata": {k: v for k, v in parsed_data.items() if k != "content"}
        }
        
        return JSONResponse(content=response)
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error parsing file: {str(e)}"}
        )
    finally:
        os.unlink(tmp_path)

@app.post("/save-text")
async def save_text(content: str = Form(...)):
    return JSONResponse(content={
        "filename": "manual_entry",
        "file_type": "text",
        "content": content,
        "metadata": {}
    })