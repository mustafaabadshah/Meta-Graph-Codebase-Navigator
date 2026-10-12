# Setup & Deployment Guide: Meta-Graph Codebase Navigator

## Prerequisites
- **Python**: Version 3.11 or 3.12 (Python 3.12.3 verified)
- **Node.js**: Version 18+ (Node.js v24.14.1 & npm 11.11.0 verified)
- **Git**: Installed and on system PATH
- **Groq API Key**: (Provided by user or obtained from [console.groq.com](https://console.groq.com))
- **Graph Database**:
  - *Option A*: Built-in persistent NetworkX store (zero external dependencies, works immediately).
  - *Option B*: Local Neo4j container (`docker compose up -d neo4j`).
  - *Option C*: Neo4j AuraDB Free cloud instance.

---

## 1. Quickstart Setup (Windows PowerShell)

### Step 1: Clone or Navigate to Project Root
```powershell
cd "E:\MM Office\Meta-Graph-Codebase-Navigator"
```

### Step 2: Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```
Ensure your `.env` contains:
```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=qwen/qwen3.8-27b
DEFAULT_REPOSITORY_PATH=E:\MM Office\Agent Chess
GRAPH_BACKEND=neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
```
*(Note: If Neo4j is not running, the system automatically runs using its persistent NetworkX store without crashing, exposing full connection diagnostics in the UI!)*

### Step 3: Install Python Dependencies
```powershell
python -m pip install -r backend/requirements.txt
```

### Step 4: Install Frontend Dependencies
```powershell
cd frontend
npm install
cd ..
```

---

## 2. Running the Application

### Option A: Run Backend & Frontend in Two Terminals

**Terminal 1 (Backend - FastAPI)**:
```powershell
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```
API Documentation will be live at: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

**Terminal 2 (Frontend - React + Vite)**:
```powershell
npm run dev --prefix frontend
```
Interactive UI will be live at: [http://127.0.0.1:5173](http://127.0.0.1:5173)

---

## 3. Neo4j Database Setup (Optional for Production Scale)

### Option 1: Local Docker Container
Run the included `docker-compose.yml`:
```powershell
docker compose up -d neo4j
```
Verify connectivity and apply schema constraints:
```powershell
python scripts/setup_neo4j.py
```
Open Neo4j Browser at: [http://localhost:7474](http://localhost:7474) (Auth: `neo4j` / `password`).

### Option 2: Neo4j AuraDB Free Cloud
1. Create a free AuraDB instance at [neo4j.com/cloud/platform/aura-graph-database](https://neo4j.com/cloud/platform/aura-graph-database/).
2. Copy the connection URI (e.g. `neo4j+s://xxxx.databases.neo4j.io`) and password into your `.env`.
3. Run the schema initialization script:
```powershell
python scripts/setup_neo4j.py
```

---

## 4. Running Verification Checks

### Run All Unit and Integration Tests
```powershell
python -m pytest backend/tests/
```

### Run Automated Architectural Benchmark
```powershell
python scripts/run_evaluation.py
```

### Verify Production Frontend Build
```powershell
npm run build --prefix frontend
```
