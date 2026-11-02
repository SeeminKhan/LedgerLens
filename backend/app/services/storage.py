import os
import uuid
import logging
from typing import Tuple
from fastapi import HTTPException, status
from supabase import create_client, Client
from app.core.config import settings

logger = logging.getLogger("ledgerlens.storage")

# Magic bytes signature definitions
FILE_SIGNATURES = {
    "application/pdf": b"%PDF",
    "image/png": b"\x89PNG\r\n\x1a\n",
    "image/jpeg": b"\xff\xd8\xff",
}


def get_supabase_client() -> Client | None:
    """Initialize and return the Supabase client using service role key."""
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        logger.warning("Supabase credentials not configured in settings.")
        return None
    try:
        return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        return None


def validate_file(filename: str, content_type: str, file_bytes: bytes) -> None:
    """
    Validate file extension, declared MIME type, magic bytes signature, and size.
    Raises HTTPException with 400 Bad Request if validation fails.
    """
    # 1. Size verification
    file_size = len(file_bytes)
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes).",
        )
    if file_size > settings.MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size ({file_size / (1024 * 1024):.2f} MB) exceeds the maximum limit of 10 MB.",
        )

    # 2. Extension verification
    _, ext = os.path.splitext(filename.lower())
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{ext}'. Allowed extensions: {', '.join(sorted(settings.ALLOWED_EXTENSIONS))}",
        )

    # 3. MIME type verification
    normalized_mime = content_type.lower()
    if normalized_mime == "image/jpg":
        normalized_mime = "image/jpeg"

    if normalized_mime not in settings.ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported MIME type '{content_type}'. Allowed types: {', '.join(sorted(settings.ALLOWED_MIME_TYPES))}",
        )

    # 4. Actual file signature (magic bytes) verification
    expected_magic = FILE_SIGNATURES.get(normalized_mime)
    if not expected_magic or not file_bytes.startswith(expected_magic):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File content signature does not match expected format for {normalized_mime}.",
        )


def upload_invoice_to_storage(filename: str, content_type: str, file_bytes: bytes) -> Tuple[str, Client | None]:
    """
    Upload the verified file bytes to the private Supabase Storage bucket.
    Returns a tuple of (storage_path, supabase_client).
    """
    _, ext = os.path.splitext(filename.lower())
    unique_id = uuid.uuid4()
    storage_path = f"invoices/{unique_id}{ext}"

    normalized_mime = "image/jpeg" if content_type.lower() == "image/jpg" else content_type.lower()

    client = get_supabase_client()
    if client:
        try:
            # Upload file bytes to private bucket
            client.storage.from_(settings.SUPABASE_BUCKET_NAME).upload(
                path=storage_path,
                file=file_bytes,
                file_options={"content-type": normalized_mime, "upsert": "false"},
            )
            logger.info(f"Successfully uploaded {filename} to {storage_path}")
        except Exception as e:
            logger.error(f"Supabase Storage upload failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to upload invoice to cloud storage: {str(e)}",
            )
    else:
        logger.warning(
            f"Running in local/mock storage mode. Simulated storage path: {storage_path}"
        )

    return storage_path, client


def delete_invoice_from_storage(storage_path: str, client: Client | None = None) -> None:
    """
    Compensation action: deletes an uploaded object if downstream database operations fail.
    Prevents orphaned files in storage.
    """
    if client is None:
        client = get_supabase_client()

    if client:
        try:
            client.storage.from_(settings.SUPABASE_BUCKET_NAME).remove([storage_path])
            logger.info(f"Cleaned up orphaned storage object at {storage_path}")
        except Exception as e:
            logger.error(f"Failed to delete orphaned file {storage_path}: {e}")

