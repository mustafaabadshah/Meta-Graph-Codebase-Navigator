import asyncio
import sys
import json
from pathlib import Path

# Add backend to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.evaluation.runner import evaluation_runner

async def main():
    print("\n=======================================================")
    print("Meta-Graph Codebase Navigator - Architectural Benchmark")
    print("Repository: Agent Chess")
    print("=======================================================\n")

    print("[*] Executing benchmark evaluation suite against verified questions...")
    result = await evaluation_runner.run_benchmark(repo_id="agent_chess")

    print(f"\n[+] Benchmark Complete! Run ID: {result['run_id']}")
    print(f"    - Total Questions Tested          : {result['total_questions']}")
    print(f"    - Symbol Retrieval Hit Rate       : {result['symbol_retrieval_hit_rate_pct']}%")
    print(f"    - Relevant File Accuracy          : {result['relevant_file_accuracy_pct']}%")
    print(f"    - Citation Line Range Validity    : {result['citation_validity_pct']}%")
    print(f"    - Average End-to-End Latency      : {result['average_latency_ms']} ms")

    print("\n[+] Breakdown by Question:")
    for r in result["results"]:
        print(f"\n  • [{r['question_id']}] ({r['category']}):")
        print(f"    Question    : {r['question'][:80]}...")
        print(f"    Symbol Hits : {r['symbol_hit_rate'] * 100}% | File Hits: {r['file_hit_rate'] * 100}% | Citations: {r['citations_count']}")
        print(f"    Latency     : {r['latency_ms']} ms")
        print(f"    Preview     : {r['answer_snippet'][:120]}...")

    print(f"\n[+] Results persisted to: data/evaluations/{result['run_id']}.json\n")

if __name__ == "__main__":
    asyncio.run(main())
