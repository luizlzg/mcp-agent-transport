"""
FastAPI application entry point for the Itinerary Generator API.

Run with: uvicorn api.main:app --reload --port 8000
"""
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import itinerary, health

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="Itinerary Generator API",
    description="API for generating travel itineraries with AI-powered agents",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(itinerary.router)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Itinerary Generator API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))

    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        reload=True,
    )
