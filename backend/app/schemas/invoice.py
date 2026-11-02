from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class InvoiceResponse(BaseModel):
    """Public schema for invoice metadata returned to clients."""
    id: UUID
    original_filename: str
    file_type: str
    file_size: int
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

