from fastapi import FastAPI, UploadFile, File, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import tempfile
from pathlib import Path
from mistralai import Mistral

from app.parsers.pdf import parse_pdf
from app.parsers.docx import parse_docx
from app.storage import save_document

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

SUPPORTED_TYPES = {
    ".pdf": parse_pdf,
    ".docx": parse_docx,
}

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    has_api_key = MISTRAL_API_KEY is not None
    return templates.TemplateResponse("index.html", {
        "request": request,
        "has_api_key": has_api_key
    })

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
        
        file_size = len(content)
        
        response = {
            "filename": file.filename,
            "file_type": file_ext,
            "content": parsed_data["content"],
            "file_size": file_size,
            "metadata": {k: v for k, v in parsed_data.items() if k != "content"},
            "temp_path": tmp_path
        }
        
        return JSONResponse(content=response)
    
    except Exception as e:
        os.unlink(tmp_path)
        return JSONResponse(
            status_code=500,
            content={"error": f"Error parsing file: {str(e)}"}
        )

@app.post("/ocr-refine")
async def ocr_refine(
    temp_path: str = Form(...),
    filename: str = Form(...),
    api_key: str = Form(None)
):
    try:
        key_to_use = api_key if api_key else MISTRAL_API_KEY
        
        if not key_to_use:
            return JSONResponse(
                status_code=400,
                content={"error": "No API key provided"}
            )
        
        if not os.path.exists(temp_path):
            return JSONResponse(
                status_code=400,
                content={"error": "Temporary file not found"}
            )
        
        client = Mistral(api_key=key_to_use)
        
        with open(temp_path, "rb") as file:
            uploaded_file = client.files.upload(
                file={
                    "file_name": filename,
                    "content": file,
                },
                purpose="ocr"
            )
        
        signed_url_response = client.files.get_signed_url(file_id=uploaded_file.id)
        signed_url = signed_url_response.url
        
        file_ext = Path(filename).suffix.lower()
        if file_ext in ['.jpg', '.jpeg', '.png']:
            document_config = {
                "type": "image_url",
                "image_url": signed_url,
            }
        else:
            document_config = {
                "type": "document_url",
                "document_url": signed_url,
            }
        
        ocr_response = client.ocr.process(
            model="mistral-ocr-latest",
            document=document_config
        )
        
        ocr_data = ocr_response.model_dump()
        
        markdown_text = ""
        for page in ocr_data.get("pages", []):
            page_number = page.get("index", "unknown")
            markdown_content = page.get("markdown", "")
            markdown_text += f"## Page {page_number}\n\n{markdown_content}\n\n---\n\n"
        
        return JSONResponse(content={
            "content": markdown_text,
            "page_count": len(ocr_data.get("pages", []))
        })
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"OCR error: {str(e)}"}
        )

@app.post("/save")
async def save(
    filename: str = Form(...),
    file_type: str = Form(...),
    content: str = Form(...),
    file_size: int = Form(None),
    temp_path: str = Form(None)
):
    try:
        doc_id = save_document(
            filename=filename,
            original_type=file_type,
            content=content,
            file_size=file_size
        )
        
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
        
        return JSONResponse(content={
            "status": "success",
            "doc_id": doc_id,
            "message": f"Document saved successfully (ID: {doc_id})"
        })
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error saving document: {str(e)}"}
        )

@app.post("/cleanup")
async def cleanup(temp_path: str = Form(...)):
    try:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        return JSONResponse(content={"status": "ok"})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.post("/save-text")
async def save_text(content: str = Form(...)):
    return JSONResponse(content={
        "filename": "manual_entry",
        "file_type": "text",
        "content": content,
        "metadata": {}
    })