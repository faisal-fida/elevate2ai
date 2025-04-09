import pytest
from fastapi import status

def test_search_media_unauthorized(client, base_url):
    """Test media search without authentication"""
    response = client.get(f"{base_url}/media/search?query=nature")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_search_media_authorized(client, base_url, auth_headers):
    """Test media search with valid authentication"""
    response = client.get(
        f"{base_url}/media/search?query=nature&limit=4",
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "images" in data
    assert isinstance(data["images"], list)
    if len(data["images"]) > 0:
        image = data["images"][0]
        assert "url" in image
        assert "width" in image
        assert "height" in image
        assert "photographer" in image

def test_search_media_invalid_query(client, base_url, auth_headers):
    """Test media search with invalid query parameter"""
    response = client.get(
        f"{base_url}/media/search?query=a",  # Query too short
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

def test_search_media_invalid_limit(client, base_url, auth_headers):
    """Test media search with invalid limit parameter"""
    response = client.get(
        f"{base_url}/media/search?query=nature&limit=30",  # Limit too high
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

def test_search_media_no_fallback(client, base_url, auth_headers):
    """Test media search without fallback option"""
    response = client.get(
        f"{base_url}/media/search?query=nature&fallback=false",
        headers=auth_headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "images" in data