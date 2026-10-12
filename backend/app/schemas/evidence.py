from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class SourceSnippetResponse(BaseModel):
    repository_id: str
    rel_path: str
    symbol: Optional[str] = None
    start_line: int
    end_line: int
    total_lines: int
    snippet: str
    full_content: Optional[str] = None
    file_hash: str
