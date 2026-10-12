from pathlib import Path
from typing import Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

# Base directory for the navigator application
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BASE_DIR / ".env", BASE_DIR / "backend" / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Application Paths
    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = BASE_DIR / "data"
    INDEXES_DIR: Path = BASE_DIR / "data" / "indexes"
    EVALUATIONS_DIR: Path = BASE_DIR / "data" / "evaluations"
    CACHE_DIR: Path = BASE_DIR / "data" / "cache"

    # Graph Storage Backend
    # Options: "auto" (default: Neo4j if available, fallback to Redis/NetworkX), "neo4j", "networkx", "redis"
    GRAPH_BACKEND: str = Field(default="auto")
    
    # Neo4j Database
    NEO4J_URI: str = Field(default="bolt://localhost:7687")
    NEO4J_USERNAME: str = Field(default="neo4j")
    NEO4J_PASSWORD: str = Field(default="password")
    NEO4J_DATABASE: str = Field(default="neo4j")

    # Redis Configuration (Cache & Graph Storage)
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    REDIS_CACHE_ENABLED: bool = Field(default=True)
    REDIS_CACHE_TTL_SECONDS: int = Field(default=300)

    # Groq LLM Configuration
    GROQ_API_KEY: Optional[str] = Field(default=None)
    GROQ_MODEL: str = Field(default="qwen/qwen3.8-27b")

    # Server & CORS
    BACKEND_HOST: str = Field(default="127.0.0.1")
    BACKEND_PORT: int = Field(default=8000)
    FRONTEND_PORT: int = Field(default=5173)
    FRONTEND_API_URL: str = Field(default="http://127.0.0.1:8000")
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]

    # Target Repository & Scanner Guardrails
    DEFAULT_REPOSITORY_PATH: str = Field(default=r"E:\MM Office\Agent Chess")
    MAX_REPOSITORY_FILES: int = Field(default=1000)
    MAX_FILE_SIZE_BYTES: int = Field(default=1024 * 1024) # 1 MB

    # Bounded Traversal Limits
    MAX_GRAPH_DEPTH: int = Field(default=4)
    MAX_GRAPH_NODES: int = Field(default=60)
    MAX_GRAPH_EDGES: int = Field(default=120)
    QUERY_TIMEOUT_SECONDS: int = Field(default=30)

    # General
    ENVIRONMENT: str = Field(default="development")
    LOG_LEVEL: str = Field(default="INFO")

settings = Settings()
