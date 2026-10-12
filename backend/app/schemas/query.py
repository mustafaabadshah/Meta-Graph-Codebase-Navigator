from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class QueryRequest(BaseModel):
    repository_id: str
    question: str
    retrieval_depth: int = Field(default=3, ge=1, le=5)
    detail_level: str = Field(default="detailed") # "concise", "detailed"

class CitationItem(BaseModel):
    repository: str
    file: str
    symbol: Optional[str] = None
    start_line: int
    end_line: int
    evidence_type: str = "verified_source"

class QueryResponse(BaseModel):
    repository_id: str
    question: str
    answer: str
    citations: List[CitationItem]
    retrieved_symbols: List[Dict[str, Any]] = Field(default_factory=list)
    graph_subgraph: Dict[str, Any] = Field(default_factory=dict)
    execution_flow: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    model_metadata: Dict[str, Any] = Field(default_factory=dict)
