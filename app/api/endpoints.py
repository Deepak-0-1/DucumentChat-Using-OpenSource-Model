from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from typing import List
import shutil
import os
from pathlib import Path
from app.core.config import settings
from app.schemas.response import ChatResponse, DocumentInfo
from app.services.document_processor import pdf_processor
from app.services.rag_service import rag_engine

router = APIRouter()

@router.post("/upload", response_model=DocumentInfo)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    
    file_path = settings.UPLOAD_DIR / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Process in background
    background_tasks.add_task(
        rag_engine.process_document,
        str(file_path)
    )
    
    return DocumentInfo(
        filename=file.filename,
        status="processing",
        message="Document is being indexed. You can start chatting shortly."
    )

@router.post("/ask", response_model=ChatResponse)
async def ask_question(question: str):
    try:
        answer = await rag_engine.ask(question)
        return ChatResponse(answer=answer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ask_stream")
async def ask_question_stream(question: str):
    return StreamingResponse(rag_engine.ask_stream(question), media_type="text/event-stream")

@router.get("/documents", response_model=List[str])
async def list_documents():
    return [f.name for f in settings.UPLOAD_DIR.iterdir() if f.is_file()]

@router.delete("/document/{filename}")
async def delete_document(filename: str):
    file_path = settings.UPLOAD_DIR / filename
    if file_path.exists():
        os.remove(file_path)
        # Also cleanup vector store if possible? 
        # Simplified: we'll just allow re-indexing to overwrite
        return {"status": "success", "message": f"Deleted {filename}"}
    raise HTTPException(status_code=404, detail="File not found")

@router.put("/document/{filename}/rename")
async def rename_document(filename: str, new_name: str):
    if not new_name.endswith(".pdf"):
        new_name += ".pdf"
    old_path = settings.UPLOAD_DIR / filename
    new_path = settings.UPLOAD_DIR / new_name
    if old_path.exists():
        os.rename(old_path, new_path)
        return {"status": "success", "new_name": new_name}
    raise HTTPException(status_code=404, detail="File not found")

@router.get("/document/{filename}/insights")
async def get_document_insights(filename: str):
    file_path = settings.UPLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
        
    try:
        import fitz
        stats = {"pages": 0, "topics": 0, "questions": 0}
        with fitz.open(file_path) as doc:
            stats["pages"] = len(doc)
            # Heuristic: topics = roughly number of bold sections or large text blocks
            # Heuristic: questions = number of question marks in text
            text = ""
            for page in doc:
                text += page.get_text()
            
            stats["questions"] = text.count("?")
            # Very rough topics estimate based on newline density vs word count
            stats["topics"] = max(3, len(text.split("\n\n")) // 10) 
            
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
