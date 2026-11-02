import io
import uuid
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.models.invoice import Invoice
from app.core.config import settings

# In-memory test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create fresh tables for each test function."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function", autouse=True)
def mock_storage():
    """Mock Supabase storage upload/delete so unit tests execute offline without network delays."""
    with patch("app.api.v1.invoices.upload_invoice_to_storage") as mock_upload, \
         patch("app.api.v1.invoices.delete_invoice_from_storage") as mock_del, \
         patch("app.main.engine", engine):
        mock_upload.side_effect = lambda filename, content_type, file_bytes: (
            f"invoices/{uuid.uuid4()}_{filename}",
            MagicMock(),
        )
        yield mock_upload, mock_del


@pytest.fixture(scope="function")
def client(db_session):
    """Override get_db with test database session."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# Helper function to generate mock file content with valid magic bytes
def get_sample_file(file_type: str, size: int = 100):
    if file_type == "pdf":
        return b"%PDF-1.4\n" + b"A" * (size - 9)
    elif file_type == "png":
        return b"\x89PNG\r\n\x1a\n" + b"B" * (size - 8)
    elif file_type == "jpg" or file_type == "jpeg":
        return b"\xff\xd8\xff\xe0" + b"C" * (size - 4)
    elif file_type == "txt":
        return b"This is a text file"
    return b"Random file content"


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

def test_jpg_upload(client):
    """1. Verify JPG upload works."""
    file_bytes = get_sample_file("jpg")
    response = client.post(
        "/invoices/upload",
        files={"file": ("invoice.jpg", io.BytesIO(file_bytes), "image/jpeg")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["original_filename"] == "invoice.jpg"
    assert data["file_type"] == "image/jpeg"
    assert data["status"] == "uploaded"
    assert "id" in data


def test_png_upload(client):
    """2. Verify PNG upload works."""
    file_bytes = get_sample_file("png")
    response = client.post(
        "/invoices/upload",
        files={"file": ("receipt.png", io.BytesIO(file_bytes), "image/png")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["original_filename"] == "receipt.png"
    assert data["file_type"] == "image/png"
    assert data["status"] == "uploaded"


def test_pdf_upload(client):
    """3. Verify PDF upload works."""
    file_bytes = get_sample_file("pdf")
    response = client.post(
        "/invoices/upload",
        files={"file": ("tax_invoice.pdf", io.BytesIO(file_bytes), "application/pdf")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["original_filename"] == "tax_invoice.pdf"
    assert data["file_type"] == "application/pdf"
    assert data["status"] == "uploaded"


def test_unsupported_file_type_rejected(client):
    """4. Unsupported file types (e.g., .txt) are rejected."""
    file_bytes = get_sample_file("txt")
    response = client.post(
        "/invoices/upload",
        files={"file": ("notes.txt", io.BytesIO(file_bytes), "text/plain")},
    )
    assert response.status_code == 400
    assert "Unsupported file extension" in response.json()["detail"]


def test_spoofed_mime_type_rejected(client):
    """Reject file with PDF extension but invalid magic bytes signature."""
    fake_pdf = b"NOT_A_REAL_PDF_FILE"
    response = client.post(
        "/invoices/upload",
        files={"file": ("fake.pdf", io.BytesIO(fake_pdf), "application/pdf")},
    )
    assert response.status_code == 400
    assert "signature does not match" in response.json()["detail"]


def test_oversized_file_rejected(client):
    """5. Oversized files (>10MB) are rejected."""
    oversized_bytes = b"%PDF" + b"X" * (settings.MAX_FILE_SIZE_BYTES + 10)
    response = client.post(
        "/invoices/upload",
        files={"file": ("large.pdf", io.BytesIO(oversized_bytes), "application/pdf")},
    )
    assert response.status_code == 400
    assert "exceeds the maximum limit" in response.json()["detail"]


def test_duplicate_filenames_do_not_overwrite(client, db_session):
    """6. Duplicate original filenames do not overwrite previous uploads."""
    file_bytes = get_sample_file("pdf")
    
    # Upload first file
    resp1 = client.post(
        "/invoices/upload",
        files={"file": ("invoice.pdf", io.BytesIO(file_bytes), "application/pdf")},
    )
    assert resp1.status_code == 201
    id1 = resp1.json()["id"]

    # Upload second file with same original filename
    resp2 = client.post(
        "/invoices/upload",
        files={"file": ("invoice.pdf", io.BytesIO(file_bytes), "application/pdf")},
    )
    assert resp2.status_code == 201
    id2 = resp2.json()["id"]

    assert id1 != id2

    # Verify both records exist in DB with unique storage paths
    inv1 = db_session.query(Invoice).filter(Invoice.id == uuid.UUID(id1)).first()
    inv2 = db_session.query(Invoice).filter(Invoice.id == uuid.UUID(id2)).first()
    assert inv1.storage_path != inv2.storage_path


def test_get_invoices_list(client):
    """9. GET /invoices returns the uploaded records in newest-first order."""
    f1 = get_sample_file("pdf")
    f2 = get_sample_file("png")

    client.post("/invoices/upload", files={"file": ("first.pdf", io.BytesIO(f1), "application/pdf")})
    client.post("/invoices/upload", files={"file": ("second.png", io.BytesIO(f2), "image/png")})

    response = client.get("/invoices")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2
    # Newest first
    assert items[0]["original_filename"] == "second.png"
    assert items[1]["original_filename"] == "first.pdf"


def test_get_invoice_by_id(client):
    """10. GET /invoices/{id} returns the correct invoice or 404."""
    file_bytes = get_sample_file("pdf")
    upload_resp = client.post(
        "/invoices/upload",
        files={"file": ("target.pdf", io.BytesIO(file_bytes), "application/pdf")},
    )
    inv_id = upload_resp.json()["id"]

    # Fetch existing
    get_resp = client.get(f"/invoices/{inv_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["original_filename"] == "target.pdf"

    # Fetch non-existing UUID
    random_id = str(uuid.uuid4())
    missing_resp = client.get(f"/invoices/{random_id}")
    assert missing_resp.status_code == 404
    assert f"Invoice with ID '{random_id}' not found" in missing_resp.json()["detail"]


def test_rollback_on_database_error(client):
    """11. Failed uploads clean up storage object to prevent orphans."""
    file_bytes = get_sample_file("pdf")

    mock_storage_client = MagicMock()
    with patch("app.api.v1.invoices.upload_invoice_to_storage", return_value=("invoices/test_path.pdf", mock_storage_client)), \
         patch("app.api.v1.invoices.delete_invoice_from_storage") as mock_delete, \
         patch.object(Session, "commit", side_effect=Exception("Database connection lost")):
        
        response = client.post(
            "/invoices/upload",
            files={"file": ("error_test.pdf", io.BytesIO(file_bytes), "application/pdf")},
        )
        assert response.status_code == 500
        # Check that the compensation deletion was triggered
        mock_delete.assert_called_once_with("invoices/test_path.pdf", client=mock_storage_client)
