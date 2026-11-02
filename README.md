# LedgerLens

> **AI-Powered Purchase Invoice Extraction & GST Validation Web Application**

---

## Project Overview

**LedgerLens** is an automated web application designed to simplify invoice processing and compliance checking for Indian businesses and accountants.

Users can upload purchase invoices (as PDF documents or scanned images), and LedgerLens leverages **Google Gemini Vision API** to extract structured invoice data (vendor details, GSTIN, line items, taxable values, and tax amounts). Extracted figures and identifiers are then fed through a rigorous, rule-based **Python validation engine** to detect calculation mismatches, verify GSTIN checksums, check tax breakdown correctness (CGST + SGST vs. IGST), and identify missing mandatory fields before saving to an audit-ready **PostgreSQL** database.

---

## Core User Workflow

```
[ User ]
   │
   ▼ 1. Upload Invoice (PDF / Image)
[ Next.js Frontend ]
   │
   ▼ 2. POST /api/v1/invoices/upload
[ FastAPI Backend ]
   │
   ├─► Store file locally in `backend/uploads/`
   │
   ├─► Send document to Gemini Vision API
   │      │
   │      ▼
   │   Extract structured JSON
   │
   ├─► Execute Python Validation Rules
   │      ├─ GSTIN format & Mod-36 checksum
   │      ├─ Math checks (Qty * Rate, Line sum = Subtotal)
   │      ├─ Tax consistency (CGST/SGST vs IGST)
   │      └─ Mandatory fields completeness
   │
   ├─► Persist Invoice & Validation Results in PostgreSQL
   │
   ▼ 3. Return JSON Response
[ Next.js Frontend ]
   │
   ▼ 4. Display Side-by-Side Review
   - Original invoice document viewer
   - Extracted data table with editable fields
   - Color-coded validation status badges & error alerts
```

---

## MVP Features

- **Document Ingestion**: Support drag-and-drop file upload for invoices in PDF, PNG, and JPG formats.
- **AI Document Extraction**: Extract vendor name, invoice number, invoice date, vendor GSTIN, buyer GSTIN, line items (description, HSN/SAC, quantity, rate, amount), subtotal, CGST, SGST, IGST, and total invoice amount.
- **Automated Rule Validation**:
  - **GSTIN Validation**: Structure check (15 alphanumeric characters) and Modulo-36 checksum verification.
  - **Arithmetic Consistency**: Verify $Quantity \times Rate = Amount$ for all items, and sum of line items equals the invoice taxable subtotal.
  - **Tax Slab & Type Logic**: Ensure intra-state transactions split equally into CGST + SGST, and inter-state transactions use IGST.
  - **Mandatory Field Detection**: Flag missing critical fields (Invoice No, Date, Vendor Name, Total).
- **Interactive Review Interface**: Modern Next.js dashboard displaying side-by-side visual comparison of the document alongside parsed data, with highlighted warnings for rule violations.
- **Audit-Ready Persistence**: Store both raw extraction outputs and validation findings in PostgreSQL.

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Frontend** | **Next.js (TypeScript, React)** | User interface, file upload, side-by-side invoice viewer, validation feedback |
| **Backend** | **Python + FastAPI** | High-performance asynchronous REST API, file handling, orchestration |
| **AI Extraction** | **Google Gemini Vision API** | Multimodal OCR and structured data extraction directly to JSON |
| **Validation Engine**| **Pure Python** | Deterministic business logic, GSTIN checksum verification, arithmetic audit |
| **Database** | **PostgreSQL** | Relational storage for invoices, line items, and validation history |
| **ORM & Migrations**| **SQLAlchemy 2.0 + Alembic** | Database schema definition, queries, and managed schema migrations |
| **Testing** | **Pytest** | Automated unit tests for validation rules and API integration tests |
| **File Storage** | **Local Filesystem** | Simple, local storage for uploaded invoice images and PDFs |

> **Architectural Pattern**: **Modular Monolith**. Kept deliberately simple and maintainable—no microservices, no message brokers, and no premature infrastructure complexity.

---

## High-Level Architecture

The project is organized cleanly into two independent but co-located workspaces:

```text
LedgerLens/
├── backend/            # FastAPI application, business logic, DB models, validation
├── frontend/           # Next.js web application
├── docs/               # Architecture and technical design documentation
├── README.md           # Project documentation and roadmap
├── DEVLOG.md           # Ongoing daily development log
└── .gitignore          # Git exclusion rules
```

