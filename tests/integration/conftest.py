import pytest
from httpx import AsyncClient
from app.main import app
## This is a setup of a HTTP client to simulate requests from test code
@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
