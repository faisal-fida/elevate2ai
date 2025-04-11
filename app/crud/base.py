from typing import Any, Optional
from supabase import Client
from app.db.supabase_client import get_supabase_client
import logging
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


class BaseCRUD:
    """Base CRUD class for Supabase"""

    def __init__(self):
        self.table_name = None
        self.supabase: Client = get_supabase_client()
        self.logger = logging.getLogger(__name__)

    def set_table_name(self, table_name: str):
        """Set the table name for the CRUD operations"""
        self.table_name = table_name
        self.logger.info(f"Table name set to {self.table_name}")
        return self

    async def get(self, id: str) -> Optional[Any]:
        """Get a record by ID"""
        try:
            result = self.supabase.table(self.table_name).select("*").eq("id", id).execute()
            if not result.data:
                return None
            return result.data[0]
        except Exception as e:
            self.logger.error(f"Error getting record {id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error processing request",
            )

    async def create(self, data: dict) -> Optional[Any]:
        """Create a new record"""
        try:
            result = self.supabase.table(self.table_name).insert(data).execute()
            if not result.data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to create record"
                )
            return result.data[0]
        except Exception as e:
            self.logger.error(f"Error creating record: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error processing request",
            )

    async def update(self, id: str, data: dict) -> Optional[Any]:
        """Update a record by ID"""
        try:
            result = self.supabase.table(self.table_name).update(data).eq("id", id).execute()
            if not result.data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to update record"
                )
            return result.data[0]
        except Exception as e:
            self.logger.error(f"Error updating record {id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error processing request",
            )

    async def delete(self, id: str) -> Optional[Any]:
        """Delete a record by ID"""
        try:
            result = self.supabase.table(self.table_name).delete().eq("id", id).execute()
            if not result.data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to delete record"
                )
            return result.data[0]
        except Exception as e:
            self.logger.error(f"Error deleting record {id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error processing request",
            )
