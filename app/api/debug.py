from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
from app.services.common.debug import get_error_details, analyze_error_logs
from app.services.common.logging import setup_logger
from app.api.auth.whatsapp import get_current_admin_user

router = APIRouter(prefix="/debug", tags=["debug"])
logger = setup_logger(__name__)


@router.get("/error/{error_id}")
async def get_error_info(
    error_id: str, _=Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    Get detailed information about a specific error by its ID.
    Only accessible by admin users.
    """
    error_data = get_error_details(error_id)
    if not error_data:
        raise HTTPException(
            status_code=404, detail=f"Error with ID {error_id} not found"
        )

    return {"error_id": error_id, "details": error_data}


@router.get("/errors")
async def list_recent_errors(
    error_type: Optional[str] = None, limit: int = 10, _=Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    List and analyze recent errors. Can be filtered by error type.
    Only accessible by admin users.
    """
    results = analyze_error_logs(error_type=error_type, limit=limit)
    return results


@router.get("/status")
async def get_system_status(_=Depends(get_current_admin_user)) -> Dict[str, Any]:
    """
    Get overall system status including error rates and recent issues.
    Only accessible by admin users.
    """
    # Get recent errors
    recent_errors = analyze_error_logs(limit=5)

    # Calculate error distribution (simplified for this example)
    error_distribution = recent_errors.get("error_counts", {})

    return {
        "status": "operational",
        "recent_errors": recent_errors.get("total_errors", 0),
        "error_distribution": error_distribution,
        "most_recent_errors": recent_errors.get("errors", [])[:3],
    }
