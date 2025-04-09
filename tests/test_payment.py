import pytest
from fastapi import status

def test_update_payment_status_unauthorized(client, base_url):
    """Test payment status update without authentication"""
    test_data = {"client_email": "faisal.fida.dev@gmail.com", "payment_status": True}
    response = client.patch(f"{base_url}/status/", json=test_data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_update_payment_status_non_admin(client, base_url, auth_headers):
    """Test payment status update with non-admin user"""
    test_data = {"client_email": "faisal.fida.dev@gmail.com", "payment_status": True}
    response = client.patch(f"{base_url}/status/", headers=auth_headers, json=test_data)
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_update_payment_status_invalid_email(client, base_url, auth_headers):
    """Test payment status update with invalid email"""
    test_data = {"client_email": "invalid_email", "payment_status": True}
    response = client.patch(f"{base_url}/status/", headers=auth_headers, json=test_data)
    assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_422_UNPROCESSABLE_ENTITY]

def test_update_payment_status_nonexistent_user(client, base_url, auth_headers):
    """Test payment status update for non-existent user"""
    test_data = {"client_email": "nonexistent@example.com", "payment_status": True}
    response = client.patch(f"{base_url}/status/", headers=auth_headers, json=test_data)
    assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]