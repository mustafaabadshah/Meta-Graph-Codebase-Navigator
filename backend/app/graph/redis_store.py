import json
from typing import Dict, List, Any, Optional
import redis

from app.graph.networkx_store import NetworkXStore
from app.parser.models import RepositoryGraph
from app.core.config import settings
from app.core.logging import logger

class RedisGraphCache:
    """
    Sub-millisecond query cache layer on top of graph backends (Neo4j / NetworkX).
    Caches subgraph traversals, search queries, and statistics with TTL.
    """
    def __init__(self, redis_url: Optional[str] = None):
        self.url = redis_url or settings.REDIS_URL
        self.client: Optional[redis.Redis] = None
        self._connected = False
        self._connect()

    def _connect(self):
        try:
            self.client = redis.Redis.from_url(self.url, decode_responses=True, socket_timeout=2.0)
            self.client.ping()
            self._connected = True
            logger.info(f"Connected to Redis cache at {self.url}")
        except Exception as e:
            self._connected = False
            self.client = None
            logger.info(f"Redis cache not available at {self.url} (cache layer bypassed): {e}")

    def is_connected(self) -> bool:
        if not self._connected or not self.client:
            return False
        try:
            return bool(self.client.ping())
        except Exception:
            self._connected = False
            return False

    def get(self, key: str) -> Optional[Any]:
        if not self.is_connected() or not self.client:
            return None
        try:
            val = self.client.get(f"mg:cache:{key}")
            if val:
                return json.loads(val)
        except Exception as e:
            logger.debug(f"Redis cache get failed for {key}: {e}")
        return None

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        if not self.is_connected() or not self.client:
            return
        try:
            ttl = ttl_seconds or settings.REDIS_CACHE_TTL_SECONDS
            self.client.set(f"mg:cache:{key}", json.dumps(value), ex=ttl)
        except Exception as e:
            logger.debug(f"Redis cache set failed for {key}: {e}")

    def clear_pattern(self, pattern: str = "mg:cache:*") -> None:
        if not self.is_connected() or not self.client:
            return
        try:
            keys = self.client.keys(pattern)
            if keys:
                self.client.delete(*keys)
                logger.info(f"Cleared {len(keys)} Redis cache keys matching {pattern}")
        except Exception as e:
            logger.debug(f"Failed clearing Redis cache pattern {pattern}: {e}")

    def get_stats(self) -> Dict[str, Any]:
        connected = self.is_connected()
        key_count = 0
        if connected and self.client:
            try:
                keys = self.client.keys("mg:*")
                key_count = len(keys)
            except Exception:
                pass
        return {
            "backend": "redis",
            "connected": connected,
            "url": self.url,
            "cached_keys": key_count,
            "ttl_seconds": settings.REDIS_CACHE_TTL_SECONDS
        }

# Global cache instance
redis_cache = RedisGraphCache()

class RedisNetworkXStore(NetworkXStore):
    """
    High-Performance Redis-Backed NetworkX Graph Store.
    Executes native NetworkX BFS/DFS traversals in memory while using
    Redis as the durable, distributed, sub-millisecond persistence tier.
    Inherits all BaseGraphStore capabilities from NetworkXStore.
    """
    def __init__(self, redis_url: Optional[str] = None):
        super().__init__()
        self.url = redis_url or settings.REDIS_URL
        self.redis_client: Optional[redis.Redis] = None
        self._connected = False
        self._init_redis()
        self._load_from_redis()

    def _init_redis(self):
        try:
            self.redis_client = redis.Redis.from_url(self.url, decode_responses=True, socket_timeout=2.0)
            self.redis_client.ping()
            self._connected = True
            logger.info(f"RedisNetworkXStore connected to Redis at {self.url}")
        except Exception as e:
            self._connected = False
            logger.warning(f"RedisNetworkXStore could not connect to Redis at {self.url}: {e}")

    def is_connected(self) -> bool:
        if not self.redis_client:
            return False
        try:
            return bool(self.redis_client.ping())
        except Exception:
            return False

    def check_connection(self) -> Dict[str, Any]:
        connected = self.is_connected()
        return {
            "backend": "redis",
            "connected": connected,
            "active": True,
            "url": self.url,
            "message": f"Connected to Redis Store and Cache at {self.url}" if connected else "Redis offline.",
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges()
        }

    def _redis_repo_key(self, repo_id: str) -> str:
        return f"mg:graph:{repo_id}"

    def _load_from_redis(self):
        if not self.is_connected() or not self.redis_client:
            return
        try:
            keys = self.redis_client.keys("mg:graph:*")
            for k in keys:
                raw_json = self.redis_client.get(k)
                if not raw_json:
                    continue
                data = json.loads(raw_json)
                repo_meta = data.get("repository", {})
                repo_id = repo_meta.get("repo_id")
                if repo_id:
                    self.repositories[repo_id] = repo_meta
                    for node in data.get("nodes", []):
                        self.graph.add_node(node["id"], **node)
                    for edge in data.get("edges", []):
                        self.graph.add_edge(
                            edge["source_id"],
                            edge["target_id"],
                            key=f"{edge['type']}:{edge.get('properties', {}).get('line', 0)}",
                            type=edge["type"],
                            **edge.get("properties", {})
                        )
            if keys:
                logger.info(f"RedisNetworkXStore loaded {len(keys)} repository graphs from Redis into RAM.")
        except Exception as e:
            logger.warning(f"RedisNetworkXStore failed loading from Redis: {e}")

    def _persist_to_redis(self, repo_id: str):
        if not self.is_connected() or not self.redis_client:
            return
        try:
            nodes = [{"id": n, **d} for n, d in self.graph.nodes(data=True) if d.get("repo_id") == repo_id or d.get("category")]
            edges = [
                {"source_id": u, "target_id": v, "type": d.get("type", "UNKNOWN"), "properties": {k: val for k, val in d.items() if k != "type"}}
                for u, v, k, d in self.graph.edges(keys=True, data=True)
                if self.graph.nodes.get(u, {}).get("repo_id") == repo_id
            ]
            payload = {
                "repository": self.repositories.get(repo_id, {}),
                "nodes": nodes,
                "edges": edges
            }
            self.redis_client.set(self._redis_repo_key(repo_id), json.dumps(payload))
            logger.info(f"Persisted graph for {repo_id} to Redis ({len(nodes)} nodes, {len(edges)} edges).")
        except Exception as e:
            logger.warning(f"Failed persisting graph to Redis for {repo_id}: {e}")

    def create_or_update_index(self, graph: RepositoryGraph) -> None:
        super().create_or_update_index(graph)
        self._persist_to_redis(graph.repo_id)
        redis_cache.clear_pattern(f"mg:cache:{graph.repo_id}:*")

    def delete_repository_index(self, repo_id: str) -> None:
        super().delete_repository_index(repo_id)
        if self.is_connected() and self.redis_client:
            try:
                self.redis_client.delete(self._redis_repo_key(repo_id))
            except Exception:
                pass
        redis_cache.clear_pattern(f"mg:cache:{repo_id}:*")

    def close(self) -> None:
        super().close()
        if self.redis_client:
            try:
                self.redis_client.close()
            except Exception:
                pass
