from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.params import Query
from app.config import settings
from app.api.webhook import verify_webhook, handle_message
from app.api.auth.router import auth_router
from app.middleware.auth import JWTAuthMiddleware
from app.db.base import Base, engine
import asyncio

# Create FastAPI app
app = FastAPI(title=settings.PROJECT_NAME, description=settings.PROJECT_DESCRIPTION)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add JWT authentication middleware with excluded paths
app.add_middleware(
    JWTAuthMiddleware,
    auto_error=True,
    exclude_paths=[
        r"^/$",
        r"^/docs.*$",
        r"^/openapi.json$",
        r"^/redoc.*$",
        r"^/webhook.*$",
        r"^/auth/whatsapp/authenticate$",
        r"^/auth/google/.*$",
        r"^/auth/session/token$",
        r"^/auth/session/refresh$",
    ],
)

# Include routers
app.include_router(auth_router, prefix="/api")


# Create database tables on startup
@app.on_event("startup")
async def create_tables():
    async def init_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    await init_db()


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
