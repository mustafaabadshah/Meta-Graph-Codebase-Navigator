from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query

from app.graph import get_graph_store
from app.graph.redis_store import redis_cache
from app.services.evidence_service import evidence_service
from app.schemas.graph import GraphSubgraphResponse, SymbolResponse, PathTraceResponse
from app.schemas.evidence import SourceSnippetResponse

router = APIRouter(prefix="/repositories/{repository_id}", tags=["Graph Exploration"])

@router.get("/graph", response_model=GraphSubgraphResponse)
def get_repository_graph(
    repository_id: str,
    view_mode: str = Query(default="architecture", description="View mode: architecture, modules, hierarchy, all"),
    focus: Optional[str] = Query(default=None, description="Optional symbol ID to focus/center on"),
    depth: int = Query(default=2, ge=1, le=4),
    limit: int = Query(default=80, ge=10, le=250)
):
    cache_key = f"subgraph:{repository_id}:{view_mode}:{focus}:{depth}:{limit}"
    cached = redis_cache.get(cache_key)
    if cached:
        return GraphSubgraphResponse(**cached)

    store = get_graph_store()
    subgraph = store.get_subgraph(
        repo_id=repository_id,
        view_mode=view_mode,
        focus_symbol_id=focus,
        depth=depth,
        limit=limit
    )
    redis_cache.set(cache_key, subgraph, ttl_seconds=120)
    return GraphSubgraphResponse(**subgraph)


@router.get("/symbols")
def search_symbols(
    repository_id: str,
    q: Optional[str] = Query(default=None, description="Symbol search string"),
    query: Optional[str] = Query(default=None, description="Alternative symbol search string"),
    limit: int = Query(default=30, ge=1, le=100)
):
    store = get_graph_store()
    search_term = q or query or ""
    return store.search_symbols(repository_id, search_term, limit=limit)

@router.get("/symbols/{symbol_id:path}/details")
def get_symbol_details(repository_id: str, symbol_id: str):
    store = get_graph_store()
    sym = store.get_symbol(symbol_id)
    if not sym:
        raise HTTPException(status_code=404, detail="Symbol not found")
    return sym

@router.get("/symbols/{symbol_id:path}/relationships")
def get_symbol_relationships(repository_id: str, symbol_id: str):
    store = get_graph_store()
    incoming = store.get_incoming_relationships(symbol_id)
    outgoing = store.get_outgoing_relationships(symbol_id)
    callers = store.get_callers(symbol_id)
    callees = store.get_callees(symbol_id)
    return {
        "symbol_id": symbol_id,
        "incoming": incoming,
        "outgoing": outgoing,
        "callers": callers,
        "callees": callees
    }

@router.get("/source", response_model=SourceSnippetResponse)
def get_source_evidence(
    repository_id: str,
    file: str = Query(..., description="Repository-relative file path"),
    start_line: Optional[int] = Query(default=None),
    end_line: Optional[int] = Query(default=None),
    symbol: Optional[str] = Query(default=None)
):
    try:
        return evidence_service.get_source_file_content(
            repo_id=repository_id,
            rel_path=file,
            start_line=start_line,
            end_line=end_line,
            symbol_name=symbol
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/paths", response_model=PathTraceResponse)
def trace_paths(
    repository_id: str,
    source_id: str = Query(..., description="Source function ID"),
    target_id: str = Query(..., description="Target function ID"),
    max_depth: int = Query(default=4, ge=1, le=6)
):
    store = get_graph_store()
    paths = store.trace_call_path(source_id, target_id, max_depth=max_depth)
    return PathTraceResponse(source_id=source_id, target_id=target_id, paths=paths)
