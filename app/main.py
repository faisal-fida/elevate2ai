from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.api.auth import router as auth_router
from app.api.payment import router as payment_router
from app.api.webhook import verify_webhook, handle_message

app = FastAPI(title=settings.PROJECT_NAME, description=settings.PROJECT_DESCRIPTION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["root"])
async def root():
    return JSONResponse(content={"status": "ok"}, status_code=status.HTTP_200_OK)

@app.get("/webhook")
async def webhook_verification(
    hub_mode: str = None,
    hub_verify_token: str = None,
    hub_challenge: str = None
) -> Response:
    return await verify_webhook(hub_mode, hub_verify_token, hub_challenge)

@app.post("/webhook")
async def webhook_handler(request: Request):
    data = await request.json()
    return await handle_message(data)

app.include_router(auth_router, tags=["auth"])
app.include_router(payment_router, prefix="/payment", tags=["payment"])
