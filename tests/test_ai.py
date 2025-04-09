import pytest
from fastapi import status

def test_generate_content_unauthorized(client, base_url):
    """Test AI content generation without authentication"""
    test_data = {"prompt": "Test prompt"}
    response = client.post(f"{base_url}/ai/generate", json=test_data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_generate_content_authorized(client, base_url, auth_headers):
    """Test AI content generation with valid authentication"""
    test_data = {"prompt": "Generate a caption for a coffee shop photo"}
    response = client.post(f"{base_url}/ai/generate", headers=auth_headers, json=test_data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "caption" in data
    assert "hashtags" in data
    assert isinstance(data["caption"], str)
    assert isinstance(data["hashtags"], list)
    assert len(data["hashtags"]) >= 3

def test_generate_content_empty_prompt(client, base_url, auth_headers):
    """Test AI content generation with empty prompt"""
    test_data = {"prompt": ""}
    response = client.post(f"{base_url}/ai/generate", headers=auth_headers, json=test_data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

def test_generate_content_long_prompt(client, base_url, auth_headers):
    """Test AI content generation with very long prompt"""
    test_data = {"prompt": "a" * 1000}
    response = client.post(f"{base_url}/ai/generate", headers=auth_headers, json=test_data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "caption" in data
    assert "hashtags" in data