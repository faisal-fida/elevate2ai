import pytest
from fastapi.testclient import TestClient
from app.main import app
from tests.test_auth_utils import create_test_user_token, create_test_admin_token


@pytest.fixture(scope="session")
def client():
    """Create a test client for the FastAPI application"""
    return TestClient(app)


@pytest.fixture(scope="session")
def auth_headers():
    """Get authentication headers with test user Bearer token"""
    token = create_test_user_token()
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope="session")
def admin_auth_headers():
    """Get authentication headers with test admin Bearer token"""
    token = create_test_admin_token()
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def base_url():
    """Get the base URL for the API"""
    return "http://localhost:8000"
