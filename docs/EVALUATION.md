# Evaluation & Benchmarking Methodology

## 1. Overview
The **Meta-Graph Benchmark Framework** provides empirical evaluation of codebase question answering, measuring both structural retrieval accuracy and grounded answer generation.

Unlike synthetic evaluations that rely on simulated files or vector cosine similarity approximations, this benchmark tests against the real **Agent Chess** codebase (`E:\MM Office\Agent Chess`).

---

## 2. Benchmark Question Suite

| ID | Category | Question | Expected Ground Truth Entities |
|---|---|---|---|
| `q1_groq_rate_limit` | Exception Handling & Retries | How does the application handle a Groq API rate limit when an agent is playing a tournament? Trace the execution path, identify retry and exception-handling logic, explain what happens when retries are exhausted, and cite every relevant file, function, and line number. | Files: `backend/app/agents/groq_agent.py`<br>Symbols: `GroqChessAgent.select_move`, `APIError`, `_select_emergency_move` |
| `q2_move_validation` | Call Tracing & Correction | How is chess move validation performed and how does the agent recover when an illegal move is proposed by the LLM? | Files: `backend/app/chess/validator.py`, `backend/app/agents/groq_agent.py`<br>Symbols: `validate_move`, `GroqChessAgent.select_move` |
| `q3_tournament_bracket` | Multi-File Architecture | Explain how TournamentService sets up tournament bracket matches and transitions into game execution. | Files: `backend/app/services/tournament_service.py`, `backend/app/services/game_service.py`<br>Symbols: `TournamentService`, `game_service` |

---

## 3. Evaluation Metrics

### 1. Symbol Retrieval Hit Rate (%)
$$\text{Hit Rate} = \frac{\text{Expected Symbols Discovered in Context}}{\text{Total Expected Ground Truth Symbols}} \times 100$$
Measures whether the AST graph traversal correctly resolves target function and class nodes.

### 2. Relevant File Accuracy (%)
$$\text{File Accuracy} = \frac{\text{Expected File Paths Cited}}{\text{Total Expected Files}} \times 100$$
Measures whether citations point to the authentic files containing the relevant logic.

### 3. Citation Validity (%)
$$\text{Citation Validity} = \frac{\text{Citations with Valid Files and Verifiable Line Bounds}}{\text{Total Citations Returned}} \times 100$$
Ensures 0% citation hallucination. Every cited file must exist in the target repository and the start/end lines must correspond to genuine source code.

### 4. End-to-End Latency (ms)
Total round-trip duration including graph query planning, multi-hop traversal, authentic source extraction, Groq LLM completion, and citation verification.

---

## 4. Running the Benchmark

Run from command line:
```powershell
python scripts/run_evaluation.py
```
Or trigger interactively via the **Evaluations Dashboard** in the React web UI.
All runs are stored as auditable JSON records in `data/evaluations/eval_<timestamp>.json`.
