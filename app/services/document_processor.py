import fitz  # PyMuPDF
import os
from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

class PDFProcessor:
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            length_function=len,
        )

    def extract_text(self, file_path: str) -> List[Document]:
        """Extract text from PDF and split into chunks."""
        documents = []
        try:
            with fitz.open(file_path) as doc:
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    text = page.get_text()
                    
                    if not text.strip():
                        continue
                        
                    # Split text belonging only to this page
                    chunks = self.text_splitter.split_text(text)
                    
                    # Create LangChain documents mapped to page
                    for i, chunk in enumerate(chunks):
                        documents.append(
                            Document(
                                page_content=chunk,
                                metadata={
                                    "source": os.path.basename(file_path),
                                    "page": page_num + 1  # 1-indexed for UI display
                                }
                            )
                        )
        except Exception as e:
            print(f"Error processing PDF {file_path}: {e}")
            raise e
            
        return documents

pdf_processor = PDFProcessor()
