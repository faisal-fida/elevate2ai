from fastapi import APIRouter
from app.api.auth.whatsapp import (
    router as whatsapp_auth_router,
)
from app.api.auth.session import router as session_router

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

auth_router.include_router(whatsapp_auth_router)
auth_router.include_router(session_router)
