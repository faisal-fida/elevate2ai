from fastapi import APIRouter
from app.api.auth import whatsapp, session

# Create auth router
auth_router = APIRouter(prefix="/auth", tags=["auth"])

# Include sub-routers
auth_router.include_router(whatsapp.router)
auth_router.include_router(session.router)
