# DocuMind API | AI-Powered Document RAG System

DocuMind is a high-performance, production-ready RAG (Retrieval-Augmented Generation) system built with **FastAPI**, **LangChain**, and **Ollama**. It allows users to upload PDF documents and engage in a contextual conversation with their data using a local LLM.

## 🚀 Impact & Key Features
- **Privacy-First**: Uses local LLMs via Ollama, ensuring data never leaves your machine.
- **Asynchronous Processing**: Non-blocking document indexing using FastAPI BackgroundTasks.
- **Premium UI**: Modern dark-mode interface with glassmorphism and real-time chat.
- **Production Scaffolding**: Modular architecture, Pydantic settings, and Docker support.
- **Vector Search**: Semantic retrieval powered by ChromaDB.

## 🛠 Tech Stack
- **Backend**: FastAPI, LangChain, ChromaDB, PyMuPDF
- **Intelligence**: Ollama (Llama 3 / Nomic Embeddings)
- **Frontend**: Vanilla JS, HTML5, CSS3 (Glassmorphism)
- **DevOps**: Docker, Docker Compose

## 📦 Getting Started

### 1. Prerequisites
- **Python 3.10+**
- **Ollama**: [Download here](https://ollama.com/download)
- Pull the required models:
  ```bash
  ollama pull gemma4
  ollama pull nomic-embed-text
  ```

### 2. Setup
1. Clone the repository and navigate to the directory.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```
4. Open your browser at `http://localhost:8000`

## 🐳 Docker Support
To run the entire stack (including Ollama) in containers:
```bash
docker-compose up --build
```

## 📄 License
MIT License
