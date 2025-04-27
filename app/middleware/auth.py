from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer
from app.services.auth.security import verify_token
from app.services.common.logging import setup_logger
from typing import Optional, List
import re

logger = setup_logger(__name__)


class JWTAuthMiddleware:
    """
    Middleware for JWT authentication
    """

    def __init__(self, auto_error: bool = True, exclude_paths: Optional[List[str]] = None):
        self.auto_error = auto_error
        self.security = HTTPBearer(auto_error=auto_error)
        self.exclude_paths = exclude_paths or []

        # Compile regex patterns for excluded paths
        self.exclude_patterns = [re.compile(pattern) for pattern in self.exclude_paths]

    async def __call__(self, request: Request, call_next):
        # Check if path should be excluded
        path = request.url.path

        for pattern in self.exclude_patterns:
            if pattern.match(path):
                return await call_next(request)

        # Get credentials
        try:
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                if self.auto_error:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Not authenticated",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                else:
                    return await call_next(request)

            scheme, credentials = auth_header.split()
            if scheme.lower() != "bearer":
                if self.auto_error:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid authentication scheme",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                else:
                    return await call_next(request)

            # Verify token
            payload = verify_token(credentials)
            if not payload:
                if self.auto_error:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid token or expired token",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                else:
                    return await call_next(request)

            # Add payload to request state
            request.state.user = payload

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication error",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        return await call_next(request)
