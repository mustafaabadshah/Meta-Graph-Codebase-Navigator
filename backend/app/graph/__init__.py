from typing import Optional, Dict, Any, List
from app.core.config import settings
from app.core.logging import logger
from app.graph.base import BaseGraphStore
from app.graph.neo4j_store import Neo4jStore
from app.graph.networkx_store import NetworkXStore
from app.graph.redis_store import RedisNetworkXStore, redis_cache

_active_store: Optional[BaseGraphStore] = None
_active_backend_mode: str = "auto"
_neo4j_diagnostic: Optional[Dict[str, Any]] = None
_redis_diagnostic: Optional[Dict[str, Any]] = None

def get_graph_store() -> BaseGraphStore:
    """
    Returns the active graph store instance based on current selection:
    'auto' (default: checks Neo4j -> Redis -> NetworkX), 'neo4j', 'redis', or 'networkx'.
    """
    global _active_store, _active_backend_mode, _neo4j_diagnostic, _redis_diagnostic
    if _active_store is not None:
        if _active_backend_mode == "auto":
            try:
                diag = _active_store.check_connection()
                if diag.get("connected", False):
                    return _active_store
                logger.warning("Active graph store disconnected in 'auto' mode. Dynamically falling back...")
                _active_store = None
            except Exception:
                _active_store = None
        else:
            return _active_store

    mode = _active_backend_mode.lower()

    if mode in ("auto", "neo4j"):
        logger.info(f"Attempting connection to Neo4j instance at {settings.NEO4J_URI}...")
        try:
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
            elif mode == "neo4j":
                # User explicitly forced Neo4j but it failed
                logger.warning(f"Neo4j was explicitly requested but is offline: {diag.get('message')}")
                _active_store = neo_store
                return _active_store
        except Exception as e:
            _neo4j_diagnostic = {"connected": False, "active": False, "message": str(e)}

    if mode in ("auto", "redis"):
        logger.info(f"Attempting connection to Redis store at {settings.REDIS_URL}...")
        try:
            redis_store = RedisNetworkXStore(redis_url=settings.REDIS_URL)
            if redis_store.is_connected():
                logger.info("RedisNetworkXStore initialized and connected successfully.")
                _redis_diagnostic = {"connected": True, "active": True, "url": settings.REDIS_URL}
                _active_store = redis_store
                return _active_store
            elif mode == "redis":
                # User explicitly forced Redis but it failed
                logger.warning("Redis was explicitly requested but is offline. Falling back to local NetworkX.")
        except Exception as e:
            _redis_diagnostic = {"connected": False, "active": False, "message": str(e)}

    # Fallback or explicit NetworkX
    logger.info("Using local persistent NetworkX graph store.")
    _active_store = NetworkXStore()
    return _active_store

def set_active_backend(backend: str) -> Dict[str, Any]:
    """
    Dynamically switches active graph backend at runtime.
    Valid options: 'auto', 'neo4j', 'redis', 'networkx'.
    """
    global _active_store, _active_backend_mode
    valid_modes = ["auto", "neo4j", "redis", "networkx"]
    backend_clean = backend.lower().strip()
    if backend_clean not in valid_modes:
        raise ValueError(f"Invalid graph backend '{backend}'. Options: {valid_modes}")

    _active_backend_mode = backend_clean
    _active_store = None  # Force re-initialization

    new_store = get_graph_store()
    return get_backend_status()

def get_backend_status() -> Dict[str, Any]:
    """
    Returns rich diagnostic status for all 3 engines + active selection mode.
    """
    global _active_store, _active_backend_mode, _neo4j_diagnostic, _redis_diagnostic
    store = get_graph_store()
    active_diag = store.check_connection()

    # Check live Neo4j status
    neo_diag = _neo4j_diagnostic
    if not neo_diag or not neo_diag.get("connected"):
        try:
            test_neo = Neo4jStore()
            neo_diag = test_neo.check_connection()
        except Exception as e:
            neo_diag = {"connected": False, "active": False, "message": str(e)}

    # Check live Redis status
    redis_stats = redis_cache.get_stats()

    return {
        "selection_mode": _active_backend_mode,
        "active_backend": active_diag.get("backend", store.__class__.__name__),
        "active_engine": store.__class__.__name__,
        "neo4j": neo_diag,
        "redis": redis_stats,
        "networkx": {
            "backend": "networkx",
            "connected": True,
            "active": isinstance(store, NetworkXStore)
        },
        "available_backends": ["auto", "neo4j", "redis", "networkx"]
    }
