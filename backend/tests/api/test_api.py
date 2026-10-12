import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_health_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"

        status_res = await client.get("/api/system/status")
        assert status_res.status_code == 200
        status_data = status_res.json()
        assert "graph_backend" in status_data

@pytest.mark.asyncio
async def test_repository_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # List repositories
        res = await client.get("/api/repositories")
        assert res.status_code == 200
        repos = res.json()
        assert isinstance(repos, list)

        # Validate invalid directory
        bad_val = await client.post("/api/repositories", json={"path": "E:/Invalid/NonExistent/Dir"})
        assert bad_val.status_code == 400

@pytest.mark.asyncio
async def test_graph_endpoints_agent_chess():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Check stats for agent_chess
        res = await client.get("/api/repositories/agent_chess/statistics")
        if res.status_code == 200:
            stats = res.json()
            assert stats["total_nodes"] > 0
            assert stats["total_edges"] > 0

        # Search symbols
        sym_res = await client.get("/api/repositories/agent_chess/symbols?q=select_move")
        if sym_res.status_code == 200:
            symbols = sym_res.json()
            assert isinstance(symbols, list)
            assert any("select_move" in (s.get("name") or "") for s in symbols)

        # Source snippet endpoint
        source_res = await client.get(
            "/api/repositories/agent_chess/source?file=backend/app/agents/groq_agent.py&start_line=50&end_line=70"
        )
        if source_res.status_code == 200:
            src_data = source_res.json()
            assert "snippet" in src_data
            assert src_data["start_line"] == 50
