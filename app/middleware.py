from fastapi import Request, status
from fastapi.security import HTTPBearer
from app.services.auth.security import verify_token
from app.logging import setup_logger
from typing import Optional, List
import re

logger = setup_logger(__name__)


class CustomJWTAuthMiddleware:
    """
    Middleware for JWT authentication
    """

    def __init__(
        self, app, auto_error: bool = True, exclude_paths: Optional[List[str]] = None
    ):
        self.app = app
        self.auto_error = auto_error
        self.security = HTTPBearer(auto_error=auto_error)
        self.exclude_paths = exclude_paths or []

        # Compile regex patterns for excluded paths
        self.exclude_patterns = [re.compile(pattern) for pattern in self.exclude_paths]

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        request = Request(scope, receive=receive)

        # Check if path should be excluded
        path = request.url.path

        for pattern in self.exclude_patterns:
            if pattern.match(path):
                return await self.app(scope, receive, send)

        # Get credentials
        try:
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                if self.auto_error:
                    return await self.handle_error(
                        scope,
                        receive,
                        send,
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Not authenticated",
                    )
                return await self.app(scope, receive, send)

            scheme, credentials = auth_header.split()
            if scheme.lower() != "bearer":
                if self.auto_error:
                    return await self.handle_error(
                        scope,
                        receive,
                        send,
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid authentication scheme",
                    )
                return await self.app(scope, receive, send)

            # Verify token
            payload = verify_token(credentials)
            if not payload:
                if self.auto_error:
                    return await self.handle_error(
                        scope,
                        receive,
                        send,
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid token or expired token",
                    )
                return await self.app(scope, receive, send)

            # Add payload to request state
            request.state.user = payload

            return await self.app(scope, receive, send)

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            if self.auto_error:
                return await self.handle_error(
                    scope,
                    receive,
                    send,
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication error",
                )
            return await self.app(scope, receive, send)

    async def handle_error(self, scope, receive, send, status_code: int, detail: str):
        from fastapi.responses import JSONResponse

        response = JSONResponse(
            status_code=status_code,
            content={"detail": detail},
            headers={"WWW-Authenticate": "Bearer"},
        )
        await response(scope, receive, send)
