import os
import json
import traceback
from typing import Dict, Any, Optional
from datetime import datetime
from app.services.common.logging import setup_logger

logger = setup_logger(__name__)

# Ensure the debug directory exists
DEBUG_DIR = "logs/debug"
os.makedirs(DEBUG_DIR, exist_ok=True)


def dump_context(
    client_id: str, context: Dict[str, Any], label: str = "context"
) -> str:
    """
    Dump the current context to a debug file for later analysis

    Args:
        client_id: The client ID
        context: The context data to dump
        label: A label for the debug dump

    Returns:
        Path to the debug file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{DEBUG_DIR}/{timestamp}_{client_id[-6:]}_{label}.json"

    try:
        # Filter out sensitive data
        filtered_context = {k: v for k, v in context.items() if not k.startswith("_")}

        with open(filename, "w") as f:
            json.dump(filtered_context, f, indent=2, default=str)

        logger.info(f"Dumped {client_id} context to {filename}")
        return filename
    except Exception as e:
        logger.error(f"Failed to dump context: {e}")
        return ""


def save_error_snapshot(
    error: Exception,
    client_id: Optional[str] = None,
    state: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Save a snapshot of the error state for debugging

    Args:
        error: The exception that occurred
        client_id: Optional client ID
        state: Optional workflow state
        context: Optional context data

    Returns:
        Error ID string for reference
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    error_id = f"{timestamp}_{id(error) % 10000}"
    if client_id:
        error_id = f"{client_id[-6:]}_{error_id}"

    filename = f"{DEBUG_DIR}/error_{error_id}.json"

    try:
        error_data = {
            "error_id": error_id,
            "timestamp": timestamp,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
        }

        if client_id:
            error_data["client_id"] = client_id

        if state:
            error_data["state"] = state

        if context:
            error_data["context"] = {k: str(v) for k, v in context.items()}

        with open(filename, "w") as f:
            json.dump(error_data, f, indent=2, default=str)

        logger.info(f"Saved error snapshot to {filename}")
        return error_id
    except Exception as e:
        logger.error(f"Failed to save error snapshot: {e}")
        return f"error_{timestamp}"


def get_error_details(error_id: str) -> Dict[str, Any]:
    """
    Retrieve error details by error ID

    Args:
        error_id: The error ID to lookup

    Returns:
        Error details or empty dict if not found
    """
    try:
        # Look for matching error files
        for filename in os.listdir(DEBUG_DIR):
            if filename.startswith(f"error_") and error_id in filename:
                with open(f"{DEBUG_DIR}/{filename}", "r") as f:
                    return json.load(f)
    except Exception as e:
        logger.error(f"Failed to get error details: {e}")

    return {}


def analyze_error_logs(
    error_type: Optional[str] = None, limit: int = 10
) -> Dict[str, Any]:
    """
    Analyze recent error logs for patterns

    Args:
        error_type: Optional filter by error type
        limit: Maximum number of errors to analyze

    Returns:
        Analysis results
    """
    errors = []
    error_counts = {}

    try:
        error_files = sorted(
            [f for f in os.listdir(DEBUG_DIR) if f.startswith("error_")], reverse=True
        )[:limit]

        for filename in error_files:
            with open(f"{DEBUG_DIR}/{filename}", "r") as f:
                error_data = json.load(f)

                if error_type and error_data.get("error_type") != error_type:
                    continue

                errors.append(error_data)

                # Count error types
                err_type = error_data.get("error_type", "Unknown")
                error_counts[err_type] = error_counts.get(err_type, 0) + 1

        return {
            "total_errors": len(errors),
            "error_counts": error_counts,
            "errors": errors[:limit],
        }
    except Exception as e:
        logger.error(f"Failed to analyze error logs: {e}")
        return {"error": str(e)}
