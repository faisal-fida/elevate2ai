import jwt
import uuid
from datetime import datetime, timedelta
from app.models.user import UserRole

# Test JWT secret key - only for testing purposes
TEST_JWT_SECRET = "test_secret_key"

def create_test_jwt(user_id: str = None, email: str = None, role: str = UserRole.USER) -> str:
    """Create a test JWT token with custom claims"""
    if not user_id:
        user_id = str(uuid.uuid4())
    if not email:
        email = f"test_{user_id}@example.com"

    # Create claims that match the structure expected by the application
    claims = {
        "aud": "authenticated",
        "exp": datetime.utcnow() + timedelta(days=1),
        "sub": user_id,
        "email": email,
        "role": role,
        "iat": datetime.utcnow(),
    }

    # Create token using the test secret
    token = jwt.encode(claims, TEST_JWT_SECRET, algorithm="HS256")
    return token

def create_test_user_token(email: str = None) -> str:
    """Create a test JWT token for a regular user"""
    return create_test_jwt(email=email, role=UserRole.USER)

def create_test_admin_token(email: str = None) -> str:
    """Create a test JWT token for an admin user"""
    return create_test_jwt(email=email, role=UserRole.ADMIN)