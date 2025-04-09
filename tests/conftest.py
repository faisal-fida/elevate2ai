import os
import pytest
from fastapi.testclient import TestClient
from dotenv import load_dotenv
from app.main import app

# Load environment variables from .env file
load_dotenv()


@pytest.fixture(scope="session")
def client():
    """Create a test client for the FastAPI application"""
    return TestClient(app)


@pytest.fixture(scope="session")
def auth_headers():
    """Get authentication headers with Bearer token from environment variables"""
    token = os.getenv("TEST_AUTH_TOKEN")
    if not token:
        raise ValueError("TEST_AUTH_TOKEN environment variable is not set")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def base_url():
    """Get the base URL for the API"""
    return "http://localhost:8000"
