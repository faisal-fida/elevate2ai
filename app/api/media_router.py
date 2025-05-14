from fastapi import APIRouter, HTTPException
from app.services.messaging.media_utils import download_from_url
from app.services.common.logging import setup_logger

logger = setup_logger(__name__)

router = APIRouter()


@router.post("/media/download-url")
async def download_media_from_url(url: str, media_type: str = "image"):
    """
    Download media from a URL and save it locally
    Returns the local URL path to the saved file
    """
    if not url:
        raise HTTPException(400, "URL is required")

    result = await download_from_url(url, media_type)
    if not result:
        raise HTTPException(500, "Failed to download media")

    _, public_url = result
    return {"media_url": public_url}


# @router.post("/media/upload")
# async def upload_media(file: UploadFile = File(...), media_type: str = "image"):
#     """
#     Upload media file and save it locally
#     Returns the local URL path to the saved file
#     """
#     try:
#         # Determine directory based on media type
#         media_dir = Path("media") / f"{media_type}s"
#         media_dir.mkdir(parents=True, exist_ok=True)

#         # Generate unique filename with proper extension
#         original_filename = file.filename or "upload"
#         file_extension = (
#             original_filename.split(".")[-1] if "." in original_filename else "jpg"
#         )
#         unique_filename = f"{uuid.uuid4()}.{file_extension}"
#         file_path = media_dir / unique_filename

#         # Save the file
#         content = await file.read()
#         with open(file_path, "wb") as f:
#             f.write(content)

#         public_url = f"/media/{media_type}s/{unique_filename}"
#         logger.info(f"File uploaded successfully to {file_path}")

#         return {"media_url": public_url}
#     except Exception as e:
#         logger.error(f"Error uploading file: {str(e)}")
#         raise HTTPException(500, f"Failed to upload file: {str(e)}")
