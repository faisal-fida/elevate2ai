import logging
from supabase import create_client, Client
from app.config import settings

logger = logging.getLogger(__name__)

supabase_client: Client | None = None


def get_supabase_client() -> Client:
    """
    Returns a Supabase client instance.
    Initializes the client on first call.
    """
    global supabase_client
    if supabase_client is None:
        logger.info("Initializing Supabase client...")
        try:
            supabase_client = create_client(
                settings.SUPABASE_URL, settings.SUPABASE_KEY
            )
            logger.info("Supabase client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}", exc_info=True)
            raise
    return supabase_client


# Optional: Initialize client on module load if preferred,
# but lazy initialization in get_supabase_client is often safer
# try:
#     get_supabase_client()
# except Exception:
#     # Log error, but allow app to potentially start if client isn't immediately needed
#     pass
