# LedgerLens — Architecture Documentation

This document outlines the initial architectural blueprint for **LedgerLens**, detailing the system design, the responsibilities of each layer, and the data flow across components.

---

## 1. Architectural Philosophy: The Modular Monolith

LedgerLens is designed as a **Modular Monolith**:
- **Why a Monolith?** For early-stage and MVP applications, microservices add unnecessary operational complexity (service discovery, network latency, distributed transactions, and multiple CI/CD pipelines). A monolith keeps everything unified in one repository with direct, predictable communication.
- **Why Modular?** Internally, the application is strictly partitioned into distinct functional boundaries (Presentation, API routing, Business Logic/Services, Persistence, and Validation). Each module has a single, well-defined responsibility, ensuring that components can be tested and modified in isolation without tangled dependencies.

---

## 2. System Architecture Diagram

```
                 ┌─────────────────────────────────────────┐
                 │             USER BROWSER                │
                 └────────────────────┬────────────────────┘
                                      │ HTTP / JSON
                                      ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ FRONTEND LAYER (Next.js + TypeScript + Tailwind CSS)                     │
│                                                                          │
│  ├── Document Upload Component (Drag & drop PDF / Images)                │
│  ├── Invoice Preview Pane (PDF / Image side-by-side view)                │
│  ├── Extracted Fields Table (Structured invoice data review)             │
│  └── Validation Alert Panel (Pass / Warning / Error status badges)       │
└─────────────────────────────────────┬────────────────────────────────────┘
                                      │ REST API Calls (HTTP Multipart & JSON)
                                      ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ BACKEND LAYER (Python + FastAPI)                                         │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ 1. API & Routing Layer (`app/api/`)                                │  │
│  │    • Request validation & deserialization                          │  │
│  │    • Multi-part file upload reception                              │  │
│  │    • Response formatting with Pydantic schemas                     │  │
│  └──────────────────┬─────────────────────────────────────────────────┘  │
│                     │                                                    │
│  ┌──────────────────▼─────────────────────────────────────────────────┐  │
│  │ 2. Service & Business Logic Layer (`app/services/`)                │  │
│  │                                                                    │  │
│  │    ├── File Service: Saves uploaded documents to local disk        │  │
│  │    │   (`backend/uploads/`)                                        │  │
│  │    │                                                               │  │
│  │    ├── Extraction Service: Calls Gemini Vision API with structured │  │
│  │    │   system prompt and strict JSON schema output                 │  │
│  │    │                                                               │  │
│  │    └── Validation Engine: Deterministic Python rules               │  │
│  │        • GSTIN format & Modulo-36 checksum calculation             │  │
│  │        • Line-item arithmetic (Qty * Rate == Amount)               │  │
│  │        • Subtotal & Tax consistency (CGST/SGST vs IGST)            │  │
│  │        • Missing mandatory fields detection                        │  │
│  └──────────────────┬─────────────────────────────────────────────────┘  │
│                     │                                                    │
│  ┌──────────────────▼─────────────────────────────────────────────────┐  │
│  │ 3. Persistence Layer (`app/db/` & `app/models/`)                   │  │
│  │    • SQLAlchemy 2.0 ORM mappings                                   │  │
│  │    • Database sessions & transactions                              │  │
│  │    • Alembic migration management                                  │  │
│  └──────────────────┬─────────────────────────────────────────────────┘  │
└─────────────────────┼────────────────────────────────────────────────────┘
                      │
       ┌──────────────┴──────────────┐
       ▼                             ▼
┌───────────────┐             ┌───────────────┐
│ Local Disk    │             │ PostgreSQL    │
│ Storage       │             │ Database      │
│ (Invoices)    │             │ (Tables)      │
└───────────────┘             └───────────────┘
```

---

## 3. Layer Responsibilities

### 3.1. Presentation Layer (`frontend/`)
- **Technology**: Next.js 14+ (App Router), TypeScript, Tailwind CSS.
- **Responsibilities**:
  - Provide a clean, intuitive interface for uploading invoices (PDF, PNG, JPG).
  - Communicate with the FastAPI backend using standard HTTP `fetch` or Axios.
  - Render an interactive split-screen view:
    - Left side: Original invoice preview.
    - Right side: Extracted fields, computed taxes, and validation diagnostics.
  - Render color-coded badges:
    - 🟢 **Pass**: Field and calculation verified.
    - 🟡 **Warning**: Minor anomaly or non-critical mismatch.
    - 🔴 **Error**: Invalid GSTIN, arithmetic error, or missing required field.

### 3.2. API & Controller Layer (`backend/app/api/`)
- **Technology**: FastAPI routers, Pydantic schemas.
- **Responsibilities**:
  - Accept and validate incoming HTTP requests and file payloads.
  - Enforce file type and file size constraints before processing.
  - Delegate execution to corresponding service modules.
  - Return predictable, strongly-typed JSON responses.

### 3.3. Service & Business Logic Layer (`backend/app/services/`)
- **Technology**: Pure Python.
- **Responsibilities**:
  - **File Storage Service**: Safely persists uploaded invoice files to the local file storage directory (`backend/uploads/`) using UUID-based filenames to avoid naming collisions and directory traversal security risks.
  - **Extraction Service**: Encapsulates all interactions with the **Google Gemini Vision API**. Prepares image/PDF payloads, attaches extraction prompts, and enforces strict JSON output adhering to our target invoice schema.
  - **Validation Service**: Contains pure, deterministic Python functions (no AI, no external network dependencies). Evaluates:
    1. *GSTIN Checksum*: Validates the 15-character alphanumeric format and verifies the 15th character using the official GSTIN Modulo 36 algorithm.
    2. *Arithmetic Integrity*: $Item \text{ } Quantity \times Item \text{ } Rate = Line \text{ } Amount$.
    3. *Total Reconciliations*: $\sum Line \text{ } Amounts = Taxable \text{ } Value$, and $Taxable \text{ } Value + Taxes = Total \text{ } Invoice \text{ } Amount$.
    4. *Tax Applicability*: Identifies whether the invoice is Intra-state (CGST + SGST) or Inter-state (IGST) based on supplier and customer state codes, and flags conflicting tax entries.
    5. *Completeness*: Ensures non-null values for mandatory accounting fields (Invoice Number, Invoice Date, Supplier Name, Total Amount).

### 3.4. Persistence Layer (`backend/app/db/` & `backend/app/models/`)
- **Technology**: PostgreSQL, SQLAlchemy 2.0 ORM, Alembic.
- **Responsibilities**:
  - Define declarative data models:
    - `Invoices`: Master record storing file path, vendor details, invoice date/number, totals, and validation status summary.
    - `LineItems`: Child records storing line item descriptions, HSN/SAC codes, quantities, rates, and amounts.
    - `ValidationLogs`: Detailed records of each validation check executed (rule name, severity, pass/fail status, and explanation message).
  - Manage database connection pooling and transactional integrity.
  - Track schema evolution predictably through versioned Alembic migration scripts.

---

## 4. End-to-End Data Flow

1. **User Upload**: The user selects or drops an invoice in the Next.js frontend.
2. **File Received**: FastAPI receives the `multipart/form-data` request, validates MIME type (PDF/PNG/JPEG), and writes the file to `backend/uploads/{uuid}.{ext}`.
3. **AI Vision Extraction**: FastAPI passes the file buffer to the Gemini Vision client. Gemini parses visual and textual data and returns a structured JSON payload.
4. **Validation Execution**: The raw parsed JSON is immediately passed to the Python Validation Engine. Rules evaluate the data sequentially and produce an audit result report.
5. **Database Commit**: In a single database transaction, the invoice header, line items, and validation check entries are committed to PostgreSQL.
6. **Response Delivery**: The complete record (invoice details + validation results) is returned to the frontend.
7. **User Review**: The frontend displays the rendered document alongside fields with inline validation feedback.

---

## 5. Security and Data Integrity Guidelines

- **No Plaintext Secrets**: API keys (Gemini) and database credentials must remain in `.env` files and never be checked into version control.
- **Local File Isolation**: All uploaded documents reside in `backend/uploads/`, which is strictly excluded via `.gitignore`.
- **Validation Before Trust**: Data returned by AI vision models is treated as untrusted input until verified by the deterministic Python validation engine.

