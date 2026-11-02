from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="LedgerLens Backend API",
    description="API for LedgerLens invoice extraction and GST validation",
    version="0.1.0",
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


@app.get("/")
def read_root():
    return {"message": "Welcome to LedgerLens API"}


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "LedgerLens Backend",
        "version": "0.1.0",
    }

