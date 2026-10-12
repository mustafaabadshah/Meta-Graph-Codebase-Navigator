from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException

from app.schemas.query import QueryRequest, QueryResponse
from app.services.query_service import query_service

router = APIRouter(prefix="/query", tags=["AI Codebase Assistant"])

@router.post("", response_model=QueryResponse)
async def ask_question(req: QueryRequest):
    try:
        return await query_service.execute_query(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history", response_model=List[Dict[str, Any]])
def get_query_history():
    return query_service.get_query_history()
