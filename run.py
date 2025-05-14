#!/usr/bin/env python
"""
Entry point for the Elevate2AI application.
Starts the FastAPI server with uvicorn.
"""

import uvicorn

if __name__ == "__main__":
    # Run the FastAPI application with uvicorn
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,  # Auto-reload on code changes (dev only)
        log_level="error",
    )
