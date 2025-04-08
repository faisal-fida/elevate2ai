from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from app.config import settings
from app.api.auth import router as auth_router
from app.api.payment import router as payment_router
from app.api.ai import router as ai_router
from app.api.media import router as media_router

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


app = FastAPI(title=settings.PROJECT_NAME, description=settings.PROJECT_DESCRIPTION)

# Set up CORS
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


app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(payment_router, prefix="/payment", tags=["payment"])
app.include_router(ai_router, prefix="/ai", tags=["ai"])
app.include_router(media_router, prefix="/media", tags=["media"])
