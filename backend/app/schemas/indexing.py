from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class GraphDiffSummary(BaseModel):
    is_incremental: bool = False
    has_changes: bool = False
    added_count: int = 0
    modified_count: int = 0
    deleted_count: int = 0
    unchanged_count: int = 0
    added_files: List[str] = Field(default_factory=list)
    modified_files: List[str] = Field(default_factory=list)
    deleted_files: List[str] = Field(default_factory=list)
    unchanged_files: List[str] = Field(default_factory=list)
    summary_text: Optional[str] = None

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
    diff: Optional[GraphDiffSummary] = None

class IndexRunResponse(BaseModel):
    repository_id: str
    status: str
    message: str
    diff: Optional[GraphDiffSummary] = None
