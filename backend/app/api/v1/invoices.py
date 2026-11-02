import uuid
from typing import List
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.invoice import Invoice
from app.schemas.invoice import InvoiceResponse
from app.services.storage import (
    validate_file,
    upload_invoice_to_storage,
    delete_invoice_from_storage,
)

router = APIRouter(prefix="/invoices", tags=["Invoices"])


@router.post(
    "/upload",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload invoice document",
    description="Upload an invoice (PDF, JPG, PNG up to 10MB) to Supabase Storage and persist metadata in PostgreSQL.",
)
async def upload_invoice(
    file: UploadFile = File(..., description="Invoice document file (PDF, PNG, JPG)"),
    db: Session = Depends(get_db),
):
    """
    Accepts an invoice document, verifies its file signature and size,
    uploads it to cloud storage, and saves its record to PostgreSQL.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must have a valid filename.",
        )

    # 1. Read file bytes
    file_bytes = await file.read()

    # 2. Comprehensive validation (Extension, MIME type, Magic Bytes, File size)
    validate_file(
        filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
        file_bytes=file_bytes,
    )

    # 3. Upload to private Supabase Storage bucket
    storage_path, storage_client = upload_invoice_to_storage(
        filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
        file_bytes=file_bytes,
    )

    # 4. Insert metadata record in PostgreSQL
    invoice = Invoice(
        original_filename=file.filename,
        storage_path=storage_path,
        file_type=file.content_type or "application/octet-stream",
        file_size=len(file_bytes),
        status="uploaded",
    )

    try:
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
    except Exception as db_err:
        db.rollback()
        # Compensation action: delete uploaded storage object to prevent orphans
        delete_invoice_from_storage(storage_path, client=storage_client)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record invoice metadata: {str(db_err)}",
        )

    return invoice


@router.get(
    "",
    response_model=List[InvoiceResponse],
    summary="List all invoices",
    description="Retrieve all uploaded invoice records ordered from newest to oldest.",
)
def list_invoices(db: Session = Depends(get_db)):
    """Retrieve all uploaded invoice records ordered by upload timestamp descending."""
    invoices = db.query(Invoice).order_by(Invoice.created_at.desc()).all()
    return invoices


@router.get(
    "/{invoice_id}",
    response_model=InvoiceResponse,
    summary="Get invoice metadata by ID",
    description="Retrieve metadata for a specific invoice by its UUID.",
)
def get_invoice(invoice_id: uuid.UUID, db: Session = Depends(get_db)):
    """Retrieve metadata for a single invoice or return 404 if not found."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice with ID '{invoice_id}' not found.",
        )
    return invoice

