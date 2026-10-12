import pytest
from unittest.mock import patch, MagicMock
from app.retrieval.workflow import create_navigator_workflow

def test_workflow_execution_mocked():
    wf = create_navigator_workflow()

    # Mock AnswerGenerator.generate to avoid live network call
    with patch("app.retrieval.answer_generator.AnswerGenerator.generate") as mock_gen:
        mock_gen.return_value = (
            "### Summary\nTest answer grounded in AST.\n\n### Execution Flow\n1. Step 1\n\n### Citations\n```json\n[{\"file\": \"backend/app/agents/groq_agent.py\", \"symbol\": \"GroqChessAgent.select_move\", \"start_line\": 59, \"end_line\": 100}]\n```",
            {"model": "test_mock", "status": "success"}
        )

        res = wf.invoke({
            "question": "How does groq agent handle rate limits?",
            "repository_id": "agent_chess",
            "retrieval_depth": 2
        })

        assert res["is_complete"] is True
        assert "Test answer grounded in AST" in res["answer"]
        assert len(res["citations"]) >= 1
        assert res["citations"][0]["file"] == "backend/app/agents/groq_agent.py"
