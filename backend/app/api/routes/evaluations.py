from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Query

from app.evaluation.runner import evaluation_runner
from app.evaluation.dataset import AGENT_CHESS_BENCHMARK

router = APIRouter(prefix="/evaluations", tags=["Evaluations & Benchmarks"])

@router.get("", response_model=List[Dict[str, Any]])
def list_evaluations():
    return evaluation_runner.list_evaluation_runs()

@router.post("/run")
async def run_evaluation(repository_id: str = Query(default="agent_chess")):
    try:
        return await evaluation_runner.run_benchmark(repo_id=repository_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/questions")
def get_benchmark_questions():
    return [q.model_dump() for q in AGENT_CHESS_BENCHMARK]
