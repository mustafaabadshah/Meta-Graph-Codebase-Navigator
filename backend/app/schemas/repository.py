from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class RepositoryCreateRequest(BaseModel):
    path: str = Field(..., description="Local absolute path to repository directory")
    name: Optional[str] = Field(None, description="Optional display name for repository")

class RepositoryResponse(BaseModel):
    id: str
    name: str
    path: str
    is_valid: bool = True
    commit_hash: Optional[str] = None
    indexed_at: Optional[str] = None
    file_count: Optional[int] = 0
    warnings: List[str] = Field(default_factory=list)

class RepositoryValidationResponse(BaseModel):
    path: str
    is_valid: bool
    exists: bool
    is_directory: bool
    is_git: bool
    commit_hash: Optional[str] = None
    estimated_python_files: int = 0
    message: str
