from typing import Optional, Dict, Any
from app.core.config import settings
from app.core.logging import logger
from app.graph.base import BaseGraphStore
from app.graph.neo4j_store import Neo4jStore
from app.graph.networkx_store import NetworkXStore

_active_store: Optional[BaseGraphStore] = None
_neo4j_diagnostic: Optional[Dict[str, Any]] = None

def get_graph_store() -> BaseGraphStore:
    global _active_store, _neo4j_diagnostic
    if _active_store is not None:
        return _active_store

    if settings.GRAPH_BACKEND.lower() == "neo4j":
        logger.info(f"Attempting connection to configured Neo4j instance at {settings.NEO4J_URI}...")
        neo_store = Neo4jStore(
            uri=settings.NEO4J_URI,
            username=settings.NEO4J_USERNAME,
            password=settings.NEO4J_PASSWORD,
            database=settings.NEO4J_DATABASE
        )
        diag = neo_store.check_connection()
        _neo4j_diagnostic = diag

        if diag["connected"]:
            logger.info("Neo4j store initialized and connected successfully.")
            _active_store = neo_store
            return _active_store
        else:
            logger.warning(
                f"[Neo4j Unavailable] Connection to {settings.NEO4J_URI} failed: {diag.get('message')}. "
                f"Falling back to local persistent NetworkX store so navigator remains operational. "
                f"To use Neo4j, start Docker ('docker compose up -d neo4j') or configure AuraDB in .env."
            )
            # Use NetworkX store
            _active_store = NetworkXStore()
            return _active_store
    else:
        logger.info("Using local NetworkX graph store as configured.")
        _active_store = NetworkXStore()
        _neo4j_diagnostic = {
            "backend": "networkx",
            "connected": True,
            "active": True,
            "message": "NetworkX backend selected via configuration."
        }
        return _active_store

def get_backend_status() -> Dict[str, Any]:
    global _active_store, _neo4j_diagnostic
    store = get_graph_store()
    active_diag = store.check_connection()
    return {
        "active_backend": active_diag.get("backend", "unknown"),
        "active_status": active_diag,
        "neo4j_status": _neo4j_diagnostic or {"connected": False, "message": "Not initialized"}
    }
