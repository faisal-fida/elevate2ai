import os
import pytest
import jwt
from datetime import datetime, timedelta
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
    """Generate test user JWT with regular user role"""
    payload = {
        "sub": "test_user",
        "role": "user",
        "exp": datetime.utcnow() + timedelta(minutes=30)
    }
    token = jwt.encode(payload, "test-secret-1234", algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope="session")
def admin_auth_headers():
    """Generate test admin JWT with admin role"""
    payload = {
        "sub": "test_admin",
        "role": "admin",
        "exp": datetime.utcnow() + timedelta(minutes=30)
    }
    token = jwt.encode(payload, "test-secret-1234", algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def base_url():
    """Get the base URL for the API"""
    return "http://localhost:8000"
