import asyncio
import os

import pytest

# Set environment variables for testing
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def async_client():
    from httpx import ASGITransport, AsyncClient

    from src.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client

@pytest.fixture
def mock_logger():
    class MockLogger:
        def info(self, msg): pass
        def error(self, msg): pass
        def warning(self, msg): pass
        def debug(self, msg): pass
    return MockLogger()
