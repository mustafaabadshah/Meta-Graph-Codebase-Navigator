from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.core.config import settings
from app.graph import get_backend_status, set_active_backend

router = APIRouter(tags=["Health & Status"])

class BackendSelectRequest(BaseModel):
    backend: str = Field(..., description="Target graph backend: 'auto', 'neo4j', 'redis', or 'networkx'")

@router.get("/health")
def get_health():
    return {
        "status": "healthy",
        "app_name": "Meta-Graph Codebase Navigator",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT
    }

@router.get("/system/status")
def get_system_status():
    backend_status = get_backend_status()
    groq_configured = bool(settings.GROQ_API_KEY)

    return {
        "status": "operational",
        "version": "1.0.0",
        "graph_backend": backend_status["active_backend"],
        "active_engine": backend_status.get("active_engine"),
        "selection_mode": backend_status.get("selection_mode", "auto"),
        "available_backends": backend_status.get("available_backends", ["auto", "neo4j", "redis", "networkx"]),
        "neo4j_connectivity": backend_status.get("neo4j", {}),
        "redis_connectivity": backend_status.get("redis", {}),
        "networkx_connectivity": backend_status.get("networkx", {}),
        "groq_configured": groq_configured,
        "groq_model": settings.GROQ_MODEL if groq_configured else None
    }

@router.post("/system/backend")
def switch_system_backend(payload: BackendSelectRequest):
    try:
        updated_status = set_active_backend(payload.backend)
        return {
            "status": "success",
            "message": f"Graph backend updated to '{payload.backend}'",
            "system": get_system_status()
        }
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed switching backend: {e}")
