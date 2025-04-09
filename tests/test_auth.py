from fastapi import status


def test_read_users_me_unauthorized(client, base_url):
    """Test accessing /users/me endpoint without authentication"""
    response = client.get(f"{base_url}/users/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_read_users_me_authorized(client, base_url, auth_headers):
    """Test accessing /users/me endpoint with valid authentication"""
    response = client.get(f"{base_url}/users/me", headers=auth_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "id" in data
    assert "email" in data
    assert "role" in data
    assert "payment_status" in data


def test_invalid_token(client, base_url):
    """Test accessing endpoint with invalid token"""
    headers = {"Authorization": "Bearer invalid_token"}
    response = client.get(f"{base_url}/users/me", headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_admin_access_non_admin(client, base_url, auth_headers):
    """Test accessing admin-only endpoint with non-admin user"""
    # Assuming the user in auth_headers is not an admin
    test_data = {"client_email": "test@example.com", "payment_status": True}
    response = client.patch(f"{base_url}/status/", headers=auth_headers, json=test_data)
    assert response.status_code == status.HTTP_403_FORBIDDEN
