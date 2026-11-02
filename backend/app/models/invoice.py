import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, Uuid, func
from app.db.base import Base


class Invoice(Base):
    """
    SQLAlchemy model representing an uploaded invoice document and its metadata.
    """
    __tablename__ = "invoices"

    # UUID primary key
    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        doc="Unique identifier for the invoice",
    )

    # Original filename uploaded by the user
    original_filename = Column(
        String(255),
        nullable=False,
        doc="Original name of the uploaded document",
    )

    # Remote object path in Supabase Storage
    storage_path = Column(
        String(500),
        nullable=False,
        unique=True,
        index=True,
        doc="Object path within the private Supabase Storage bucket",
    )

    # MIME type (e.g., application/pdf, image/png, image/jpeg)
    file_type = Column(
        String(100),
        nullable=False,
        doc="MIME type of the invoice file",
    )

    # File size in bytes
    file_size = Column(
        Integer,
        nullable=False,
        doc="File size in bytes (max 10MB)",
    )

    # Current processing status (e.g., 'uploaded', 'processing', 'validated')
    status = Column(
        String(50),
        nullable=False,
        default="uploaded",
        doc="Current pipeline status of the invoice record",
    )

    # Timestamp of creation
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        doc="Timestamp when the invoice was uploaded",
    )

    def to_dict(self):
        """Serialize invoice model to a clean dictionary."""
        return {
            "id": str(self.id),
            "original_filename": self.original_filename,
            "storage_path": self.storage_path,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

