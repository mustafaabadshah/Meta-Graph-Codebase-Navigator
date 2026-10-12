from typing import List
from fastapi import APIRouter, HTTPException

from app.schemas.repository import RepositoryCreateRequest, RepositoryResponse, RepositoryValidationResponse
from app.services.repository_service import repository_service
from app.graph import get_graph_store

router = APIRouter(prefix="/repositories", tags=["Repositories"])

@router.get("", response_model=List[RepositoryResponse])
def list_repositories():
    return repository_service.list_repositories()

@router.post("", response_model=RepositoryResponse)
def register_repository(req: RepositoryCreateRequest):
    try:
        return repository_service.register_repository(req.path, req.name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{repository_id}", response_model=RepositoryResponse)
def get_repository(repository_id: str):
    try:
        return repository_service.get_repository(repository_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/{repository_id}")
def delete_repository(repository_id: str):
    try:
        # Delete graph index
        store = get_graph_store()
        store.delete_repository_index(repository_id)
        # Delete from registry
        repository_service.delete_repository(repository_id)
        return {"status": "deleted", "repository_id": repository_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{repository_id}/validate", response_model=RepositoryValidationResponse)
def validate_repository(repository_id: str):
    try:
        repo = repository_service.get_repository(repository_id)
        return repository_service.validate_path(repo.path)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
