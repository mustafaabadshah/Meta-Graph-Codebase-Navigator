from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class GraphStatisticsResponse(BaseModel):
    repository_id: str
    total_nodes: int
    total_edges: int
    nodes_by_type: Dict[str, int]
    edges_by_type: Dict[str, int]

class SymbolResponse(BaseModel):
    id: str
    type: str
    name: str
    qualified_name: Optional[str] = None
    rel_path: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    docstring: Optional[str] = None
    is_async: Optional[bool] = None
    is_method: Optional[bool] = None
    parameters: Optional[List[str]] = None
    raises: Optional[List[str]] = None
    handles: Optional[List[str]] = None
    diff_status: Optional[str] = None

class GraphSubgraphResponse(BaseModel):
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    diff_summary: Optional[Dict[str, Any]] = None

class PathTraceResponse(BaseModel):
    source_id: str
    target_id: str
    paths: List[Dict[str, Any]]
