from pydantic import BaseModel
from typing import Optional

class ChatResponse(BaseModel):
    answer: str

class DocumentInfo(BaseModel):
    filename: str
    status: str
    message: Optional[str] = None
