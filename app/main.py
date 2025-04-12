from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.api.auth import router as auth_router
from app.api.payment import router as payment_router


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


app.include_router(auth_router, tags=["auth"])
app.include_router(payment_router, prefix="/payment", tags=["payment"])
