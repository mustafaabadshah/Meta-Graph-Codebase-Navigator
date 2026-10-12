from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class IndexStatusResponse(BaseModel):
    repository_id: str
    status: str # "idle", "running", "completed", "failed"
    progress_percentage: float = 0.0
    current_file: Optional[str] = None
    scanned_files: int = 0
    indexed_files: int = 0
    failed_files: int = 0
    total_files: int = 0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)

class IndexRunResponse(BaseModel):
    repository_id: str
    status: str
    message: str
