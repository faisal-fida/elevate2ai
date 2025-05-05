"""
Authentication Examples

This file contains examples of how to use the authentication endpoints in the API.
"""

import requests
import json

# Base URL of the API
BASE_URL = "http://localhost:8000"


def authenticate_whatsapp(whatsapp_number):
    """
    Authenticate a user using WhatsApp number

    Args:
        whatsapp_number (str): The WhatsApp number to authenticate

    Returns:
        dict: The authentication response containing user data and session tokens
    """
    url = f"{BASE_URL}/api/auth/whatsapp/authenticate"

    # Prepare request data
    data = {
        "whatsapp_number": whatsapp_number,
        "device_info": {"device_type": "web", "browser": "chrome"},
    }

    # Make request
    response = requests.post(url, json=data)

    # Check if request was successful
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Authentication failed: {response.status_code} - {response.text}")
        return None


def verify_whatsapp_number(whatsapp_number):
    """
    Verify a WhatsApp number

    Args:
        whatsapp_number (str): The WhatsApp number to verify

    Returns:
        dict: The verification response
    """
    url = f"{BASE_URL}/api/auth/whatsapp/verify/{whatsapp_number}"

    # Make request
    response = requests.post(url)

    # Check if request was successful
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Verification failed: {response.status_code} - {response.text}")
        return None


def start_google_oauth(whatsapp_number):
    """
    Start Google OAuth flow

    Args:
        whatsapp_number (str): The WhatsApp number to link with Google

    Returns:
        str: The Google OAuth URL to redirect the user to
    """
    url = f"{BASE_URL}/api/auth/google/authorize?whatsapp_number={whatsapp_number}"

    # Make request - this will redirect to Google
    print(f"Open this URL in your browser: {url}")
    return url


def get_user_profile(access_token):
    """
    Get the current user's profile using an access token

    Args:
        access_token (str): The access token from authentication

    Returns:
        dict: The user profile data
    """
    url = f"{BASE_URL}/api/auth/whatsapp/me"

    # Prepare headers with token
    headers = {"Authorization": f"Bearer {access_token}"}

    # Make request
    response = requests.get(url, headers=headers)

    # Check if request was successful
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to get profile: {response.status_code} - {response.text}")
        return None


def refresh_token(refresh_token):
    """
    Refresh an access token using a refresh token

    Args:
        refresh_token (str): The refresh token from authentication

    Returns:
        dict: The new token data
    """
    url = f"{BASE_URL}/api/auth/session/refresh"

    # Prepare request data
    data = {"refresh_token": refresh_token}

    # Make request
    response = requests.post(url, json=data)

    # Check if request was successful
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Token refresh failed: {response.status_code} - {response.text}")
        return None


def update_user_profile(
    access_token, name=None, email=None, profile_picture=None, metadata=None
):
    """
    Update the user's profile

    Args:
        access_token (str): The access token from authentication
        name (str, optional): The user's name
        email (str, optional): The user's email
        profile_picture (str, optional): URL to the user's profile picture
        metadata (dict, optional): Additional metadata for the user

    Returns:
        dict: The updated user profile
    """
    url = f"{BASE_URL}/api/auth/whatsapp/profile"

    # Prepare headers with token
    headers = {"Authorization": f"Bearer {access_token}"}

    # Prepare request data
    data = {}
    if name:
        data["name"] = name
    if email:
        data["email"] = email
    if profile_picture:
        data["profile_picture"] = profile_picture
    if metadata:
        data["metadata"] = metadata

    # Make request
    response = requests.put(url, json=data, headers=headers)

    # Check if request was successful
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Profile update failed: {response.status_code} - {response.text}")
        return None


# Example usage
if __name__ == "__main__":
    # Example WhatsApp number (replace with a real one)
    whatsapp_number = "923408957390"

    # Step 1: Authenticate with WhatsApp number
    print("Step 1: Authenticating with WhatsApp number...")
    auth_result = authenticate_whatsapp(whatsapp_number)

    if auth_result:
        print("Authentication successful!")
        print(f"User: {auth_result['user']}")

        # Extract tokens
        access_token = auth_result["session"]["access_token"]
        refresh_token = auth_result["session"]["refresh_token"]

        # Step 2: Get user profile
        print("\nStep 2: Getting user profile...")
        profile = get_user_profile(access_token)

        if profile:
            print(f"Profile: {profile}")

            # Step 3: Update user profile
            print("\nStep 3: Updating user profile...")
            updated_profile = update_user_profile(
                access_token,
                name="Test User",
                email="test@example.com",
                metadata={"preferences": {"theme": "dark"}},
            )

            if updated_profile:
                print(f"Updated profile: {updated_profile}")

            # Step 4: Refresh token
            print("\nStep 4: Refreshing token...")
            new_tokens = refresh_token(refresh_token)

            if new_tokens:
                print(f"New access token: {new_tokens['access_token']}")

                # Update access token for future requests
                access_token = new_tokens["access_token"]

        # Step 5: Start Google OAuth flow (this will print a URL to open in browser)
        print("\nStep 5: Starting Google OAuth flow...")
        oauth_url = start_google_oauth(whatsapp_number)
        print(f"Open this URL in your browser to link your Google account: {oauth_url}")
