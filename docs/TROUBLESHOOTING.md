# Troubleshooting Guide: Meta-Graph Codebase Navigator

## 1. Neo4j Connection Issues

### Symptom: `Neo4j unreachable: [WinError 10061] No connection could be made because the target machine actively refused it`
**Cause**: The local Neo4j service or Docker container is not currently running on `bolt://localhost:7687`.
**Resolution**:
1. Meta-Graph automatically detects this and falls back to its built-in **NetworkX store**, allowing all indexing, graph querying, and assistant features to function immediately without crashing.
2. To start local Neo4j with Docker:
   ```powershell
   docker compose up -d neo4j
   ```
3. Once running, apply constraints using:
   ```powershell
   python scripts/setup_neo4j.py
   ```
4. If using **Neo4j AuraDB Free**, set your cloud URI in `.env`:
   ```env
   NEO4J_URI=neo4j+s://<instance-id>.databases.neo4j.io
   NEO4J_USERNAME=neo4j
   NEO4J_PASSWORD=<your-aura-password>
   ```

---

## 2. Groq LLM API Rate Limits & Token Quotas

### Symptom: `Error code: 429 - output tokens per minute (OTPM): Limit 1000, Requested 1016`
**Cause**: The Groq on-demand free tier enforces an Output Tokens Per Minute (OTPM) cap on certain models if `max_tokens` is configured too high.
**Resolution**:
1. Meta-Graph Codebase Navigator automatically restricts `max_tokens` to 800 in `AnswerGenerator` to fit safely within the 1,000 OTPM ceiling.
2. If rate limits are encountered, the system applies **exponential backoff with jitter** (`backoff *= 2.0`).
3. If Groq rate limits are completely exhausted, the system automatically falls back to an **AST-grounded deterministic answer generator**, preventing blank or failed responses.
4. You can also switch models in `.env`:
   ```env
   GROQ_MODEL=openai/gpt-oss-20b
   ```

---

## 3. Windows Paths with Spaces

### Symptom: `FileNotFoundError` or path parsing errors when referencing paths like `E:\MM Office\Agent Chess`.
**Resolution**:
1. All path handling in the navigator utilizes `pathlib.Path` with canonical resolution (`.expanduser().resolve()`).
2. Graph entity IDs and API endpoints use normalized forward-slash POSIX paths (`backend/app/agents/groq_agent.py`) to prevent backslash escaping anomalies across JSON and URLs.
3. When using CLI scripts in PowerShell, always enclose paths in quotes:
   ```powershell
   python scripts/index_repository.py --repo-path "E:\MM Office\Agent Chess"
   ```

---

## 4. Port Conflicts

- **Port 8000 (FastAPI Backend)**: If another service uses port 8000, change `BACKEND_PORT=8001` in `.env` and run:
  ```powershell
  python -m uvicorn app.main:app --app-dir backend --port 8001 --reload
  ```
- **Port 5173 (React Frontend)**: If port 5173 is occupied, Vite will automatically offer port 5174 or you can specify `npm run dev --prefix frontend -- --port 5174`.
