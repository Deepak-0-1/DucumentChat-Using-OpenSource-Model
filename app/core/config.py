from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    # API Settings
    PROJECT_NAME: str = "DocuMind API"
    API_V1_STR: str = "/api/v1"
    
    # Storage Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    DATA_DIR: Path = BASE_DIR / "data"
    
    # Ollama Settings
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "gemma4"
    EMBEDDING_MODEL: str = "nomic-embed-text"
    
    # Vector DB Settings
    CHROMA_DB_PATH: str = str(DATA_DIR / "chroma_db")
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()

# Ensure directories exist
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
