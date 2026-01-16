"""
Pydantic schemas for API request/response validation.
"""
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class GenerateRequest(BaseModel):
    """Request model for itinerary generation."""
    attractions: str = Field(..., min_length=3, description="List of attractions to visit")
    preferences: str = Field(default="", description="Optional user preferences")
    num_days: int = Field(..., ge=1, le=14, description="Number of days for the itinerary")
    language: str = Field(default="en", pattern="^(en|pt-br|es|fr)$", description="Output language")
    email: Optional[EmailStr] = Field(default=None, description="Email to send itinerary to")
    send_email: bool = Field(default=False, description="Whether to send via email")


class GenerateResponse(BaseModel):
    """Response model after starting generation."""
    job_id: str
    stream_url: str
    message: str = "Itinerary generation started"


class JobStatus(BaseModel):
    """Model for job status."""
    job_id: str
    status: str  # pending, running, completed, failed
    document_path: Optional[str] = None
    costs_by_currency: Optional[dict] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str = "healthy"
    service: str = "itinerary-generator-api"


class UserResponse(BaseModel):
    """Request model for user response to approval prompts."""
    response: str = Field(..., min_length=1, description="User's response (e.g., 'yes' or feedback)")


class UserResponseResult(BaseModel):
    """Response model after submitting user response."""
    success: bool
    message: str
    stream_url: Optional[str] = None
