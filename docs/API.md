# REST API Reference: Meta-Graph Codebase Navigator

Base URL: `http://127.0.0.1:8000/api`

---

## 1. System & Health

### `GET /health`
Returns service vitality.
**Response**:
```json
{
  "status": "healthy",
  "app_name": "Meta-Graph Codebase Navigator",
  "version": "1.0.0",
  "environment": "development"
}
```

### `GET /system/status`
Returns connectivity details for graph storage backends and LLM configuration.
**Response**:
```json
{
  "status": "operational",
  "version": "1.0.0",
  "graph_backend": "networkx",
  "graph_details": {
    "backend": "networkx",
    "connected": true,
    "active": true
  },
  "neo4j_connectivity": {
    "connected": false,
    "troubleshooting": "Ensure local Neo4j is running ('docker compose up -d neo4j') or configure valid AuraDB credentials in .env"
  },
  "groq_configured": true,
  "groq_model": "qwen/qwen3.8-27b"
}
```

---

## 2. Repositories

### `GET /repositories`
List all registered repository workspaces.

### `POST /repositories`
Register a new local repository path.
**Request**:
```json
{
  "path": "E:\\MM Office\\Agent Chess",
  "name": "Agent Chess"
}
```

### `DELETE /repositories/{repository_id}`
Deletes graph data and registration for the specified repository. Does not delete any disk files.

---

## 3. Indexing

### `POST /repositories/{repository_id}/index`
Trigger background AST parsing and graph ingestion.

### `POST /repositories/{repository_id}/reindex`
Trigger incremental re-indexing based on SHA-256 file hashes.

### `GET /repositories/{repository_id}/index-status`
Poll indexing progress.
**Response**:
```json
{
  "repository_id": "agent_chess",
  "status": "completed",
  "progress_percentage": 100.0,
  "scanned_files": 48,
  "indexed_files": 48,
  "failed_files": 0,
  "total_files": 48,
  "completed_at": "2026-10-09T08:22:19Z"
}
```

### `GET /repositories/{repository_id}/statistics`
Returns entity and relationship breakdown.

---

## 4. Graph Exploration

### `GET /repositories/{repository_id}/graph?depth=2&limit=60`
Retrieves bounded subgraph for React Flow rendering.

### `GET /repositories/{repository_id}/symbols?q=select_move`
Searches symbols by name or qualified name.

### `GET /repositories/{repository_id}/source?file=path/to/file.py&start_line=10&end_line=40`
Retrieves verified source code lines with SHA-256 hash validation.

### `GET /repositories/{repository_id}/paths?source_id={src}&target_id={dst}`
Finds directed execution call chains between two function nodes.

---

## 5. Question Answering

### `POST /query`
Executes multi-hop retrieval and LangGraph grounded answer generation.
**Request**:
```json
{
  "repository_id": "agent_chess",
  "question": "How does the application handle a Groq API rate limit when an agent is playing a tournament?",
  "retrieval_depth": 3,
  "detail_level": "detailed"
}
```
**Response**:
```json
{
  "repository_id": "agent_chess",
  "question": "How does the application handle a Groq API rate limit when an agent is playing a tournament?",
  "answer": "### Summary\nWhen a Groq API rate limit occurs...",
  "citations": [
    {
      "repository": "agent_chess",
      "file": "backend/app/agents/groq_agent.py",
      "symbol": "GroqChessAgent.select_move",
      "start_line": 59,
      "end_line": 266,
      "evidence_type": "verified_source"
    }
  ],
  "retrieved_symbols": [...],
  "graph_subgraph": { "nodes": [...], "edges": [...] },
  "execution_flow": [...],
  "model_metadata": {
    "model": "qwen/qwen3.8-27b",
    "latency_ms": 2167,
    "status": "success"
  }
}
```
