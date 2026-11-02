from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.invoices import router as invoices_router
from app.db.base import Base
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure tables exist on startup if database is reachable
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        # Tables will be managed via Alembic migrations
        pass
    yield


app = FastAPI(
    title="LedgerLens Backend API",
    description="API for LedgerLens invoice extraction and GST validation",
    version="0.2.0",
    lifespan=lifespan,
)

# Configure CORS to permit requests from the Next.js frontend
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount invoice routers
app.include_router(invoices_router)
app.include_router(invoices_router, prefix="/api/v1")


@app.get("/")
def read_root():
    return {"message": "Welcome to LedgerLens API"}


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "LedgerLens Backend",
        "version": "0.2.0",
    }
