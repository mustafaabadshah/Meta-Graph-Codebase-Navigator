from fastapi import APIRouter
from app.core.config import settings
from app.graph import get_backend_status

router = APIRouter(tags=["Health & Status"])

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
        "graph_details": backend_status["active_status"],
        "neo4j_connectivity": backend_status["neo4j_status"],
        "groq_configured": groq_configured,
        "groq_model": settings.GROQ_MODEL if groq_configured else None
    }
