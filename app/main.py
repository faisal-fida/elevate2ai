from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.params import Query
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.api.webhook import verify_webhook, handle_message
from app.api.auth.router import auth_router
from .middleware import CustomJWTAuthMiddleware
from app.db import Base, engine, get_db
from app.services.auth.whatsapp import AuthService
from app.services.common.logging import setup_logger

logger = setup_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created.")

    logger.info("Ensuring admin user exists...")
    async_db_session_gen = get_db()

    try:
        db: AsyncSession = await async_db_session_gen.__anext__()  # Get a session
        await AuthService.ensure_admin_exists(db)
        logger.info("Admin user check complete.")
    except StopAsyncIteration:
        logger.error("Failed to get DB session for admin user creation during startup.")
    except Exception as e:
        logger.error(f"Error during admin user creation at startup: {e}")
    finally:
        try:
            await async_db_session_gen.aclose()
        except Exception:
            pass

    yield
    logger.info("Application shutdown.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    ],
)

app.include_router(auth_router, prefix="/api")


@app.get("/", tags=["root"])
async def root():
    return JSONResponse(content={"status": "ok"}, status_code=status.HTTP_200_OK)


@app.get("/webhook")
async def webhook_verification(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
) -> Response:
    return await verify_webhook(hub_mode, hub_verify_token, hub_challenge)


@app.post("/webhook")
async def webhook_handler(request: Request):
    data = await request.json()
    return await handle_message(data)
