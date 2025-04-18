from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.params import Query
from app.config import settings
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
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
) -> Response:
    return await verify_webhook(hub_mode, hub_verify_token, hub_challenge)


@app.post("/webhook")
async def webhook_handler(request: Request):
    data = await request.json()
    return await handle_message(data)
