from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.params import Query
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import Base, engine, get_db
from app.middleware import CustomJWTAuthMiddleware
from app.api.webhook import verify_webhook, handle_message
from app.api.auth.whatsapp import router as whatsapp_auth_router
from app.api.auth.session import router as session_router
from app.services.auth.whatsapp import AuthService
from app.logging import setup_logger

logger = setup_logger(__name__)

# Create media directories if they don't exist
media_path = Path("media")
media_path.mkdir(exist_ok=True)
(media_path / "images").mkdir(exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown events handler
    - Creates database tables
    - Ensures admin user exists
    - Handles graceful shutdown
    """
    # Setup database
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")

    # Create admin user if needed
    async_db_session_gen = get_db()
    try:
        db: AsyncSession = await async_db_session_gen.__anext__()
        await AuthService.ensure_admin_exists(db)
        logger.info("Admin user check complete")
    except Exception as e:
        logger.error(f"Error during admin user creation: {e}")
    finally:
        try:
            await async_db_session_gen.aclose()
        except Exception:
            pass

    yield
    logger.info("Application shutdown")


# Initialize FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup JWT authentication middleware
app.add_middleware(
    CustomJWTAuthMiddleware,
    auto_error=True,
    exclude_paths=[
        r"^/$",
        r"^/docs.*$",
        r"^/openapi.json$",
        r"^/redoc.*$",
        r"^/webhook.*$",
        r"^/api/auth/register$",
        r"^/api/auth/login$",
        r"^/api/auth/session/refresh$",
        r"^/favicon\\.ico$",
        r"^/media/.*$",
    ],
)

# Mount static media directory
app.mount("/media", StaticFiles(directory="media"), name="media")

# Setup auth router
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
auth_router.include_router(whatsapp_auth_router)
auth_router.include_router(session_router)

# Include routers
app.include_router(auth_router, prefix="/api")


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    return JSONResponse(content={"status": "ok"}, status_code=status.HTTP_200_OK)


# WhatsApp webhook endpoints
@app.get("/webhook")
async def webhook_verification(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
) -> Response:
    return await verify_webhook(hub_mode, hub_verify_token, hub_challenge)


@app.post("/webhook")
async def webhook_handler(request: Request):
    try:
        data = await request.json()
        return await handle_message(data)
    except Exception as e:
        logger.error(f"Error handling webhook: {e}")
        return JSONResponse(
            content={"status": "error", "message": str(e)},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
