from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import NavigatorException
from app.graph import get_graph_store
from app.api.routes import (
    health,
    repositories,
    indexing,
    graph,
    query,
    evaluations
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting Meta-Graph Codebase Navigator Backend on {settings.BACKEND_HOST}:{settings.BACKEND_PORT}")
    logger.info(f"Default target repository: {settings.DEFAULT_REPOSITORY_PATH}")
    store = get_graph_store()
    yield
    logger.info("Shutting down Meta-Graph Codebase Navigator Backend...")
    store.close()

app = FastAPI(
    title="Meta-Graph Codebase Navigator API",
    description="Structural Source-Code Knowledge Graph & Architectural Reasoning Engine",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Error Handlers
@app.exception_handler(NavigatorException)
async def navigator_exception_handler(request: Request, exc: NavigatorException):
    logger.warning(f"Navigator exception on {request.url.path}: {exc.message}")
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.__class__.__name__,
            "message": exc.message,
            "details": exc.details
        }
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred processing your request."
        }
    )

@app.get("/", tags=["Root"])
def root():
    return {
        "app": "Meta-Graph Codebase Navigator API",
        "status": "online",
        "version": "1.0.0",
        "frontend_ui": "http://localhost:5173",
        "api_docs": "/docs",
        "endpoints": {
            "health": "/api/health",
            "system_status": "/api/system/status",
            "repositories": "/api/repositories",
            "query": "/api/query",
            "evaluations": "/api/evaluations"
        }
    }

# Register API Routers
app.include_router(health.router, prefix="/api")
app.include_router(repositories.router, prefix="/api")
app.include_router(indexing.router, prefix="/api")
app.include_router(graph.router, prefix="/api")
app.include_router(query.router, prefix="/api")
app.include_router(evaluations.router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=True
    )
