from fastapi import APIRouter, HTTPException

from app.schemas.indexing import IndexStatusResponse, IndexRunResponse, GraphDiffSummary
from app.schemas.graph import GraphStatisticsResponse
from app.services.indexing_service import indexing_service
from app.graph import get_graph_store

router = APIRouter(prefix="/repositories/{repository_id}", tags=["Indexing"])

@router.post("/index", response_model=IndexStatusResponse)
async def start_index(repository_id: str):
    try:
        return await indexing_service.start_indexing(repository_id, is_reindex=False)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/reindex", response_model=IndexStatusResponse)
async def start_reindex(repository_id: str):
    try:
        return await indexing_service.start_indexing(repository_id, is_reindex=True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/index-status", response_model=IndexStatusResponse)
def get_index_status(repository_id: str):
    return indexing_service.get_status(repository_id)

@router.get("/diff", response_model=GraphDiffSummary)
def get_graph_diff(repository_id: str):
    try:
        return indexing_service.get_graph_diff(repository_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/statistics", response_model=GraphStatisticsResponse)
def get_repository_statistics(repository_id: str):
    store = get_graph_store()
    stats = store.get_graph_statistics(repository_id)
    return GraphStatisticsResponse(**stats)
