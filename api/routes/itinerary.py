"""
Itinerary generation API routes.
"""
import asyncio
import json
from pathlib import Path
from typing import AsyncGenerator

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from api.schemas import GenerateRequest, GenerateResponse, JobStatus, UserResponse, UserResponseResult
from api.services.runner import (
    create_job,
    get_job,
    get_job_events,
    run_graph_with_streaming,
    submit_user_response,
)

router = APIRouter(prefix="/api/v1/itinerary", tags=["itinerary"])


@router.post("/generate", response_model=GenerateResponse)
async def generate_itinerary(
    request: GenerateRequest,
    background_tasks: BackgroundTasks,
):
    """
    Start itinerary generation.

    Returns a job_id that can be used to stream progress and download the result.
    """
    # Create job
    job_id = create_job()

    # Start background task
    background_tasks.add_task(
        run_graph_with_streaming,
        job_id=job_id,
        attractions=request.attractions,
        preferences=request.preferences,
        num_days=request.num_days,
        language=request.language,
        email=request.email,
        send_email=request.send_email,
    )

    return GenerateResponse(
        job_id=job_id,
        stream_url=f"/api/v1/itinerary/stream/{job_id}",
        message="Itinerary generation started",
    )


@router.get("/stream/{job_id}")
async def stream_progress(job_id: str):
    """
    Stream progress events for a job using Server-Sent Events (SSE).

    Events include:
    - job_started: Generation has begun
    - step_started: A processing step has started
    - step_completed: A processing step has completed
    - day_organizing: Organizing attractions by day
    - day_researching: Researching attractions
    - document_generating: Building the document
    - document_ready: Document is ready for download
    - email_sent: Email delivery status
    - job_completed: All processing is done
    - job_failed: An error occurred
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator() -> AsyncGenerator[str, None]:
        async for event in get_job_events(job_id):
            event_type = event.get("type", "message")
            event_data = json.dumps(event.get("data", {}))
            yield f"event: {event_type}\ndata: {event_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/status/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """
    Get the current status of a job.
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatus(
        job_id=job_id,
        status=job.get("status", "unknown"),
        document_path=job.get("document_path"),
        costs_by_currency=job.get("costs_by_currency"),
        error=job.get("error"),
    )


@router.get("/download/{job_id}")
async def download_document(job_id: str):
    """
    Download the generated itinerary document.
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.get("status") != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job is not completed. Current status: {job.get('status')}",
        )

    document_path = job.get("document_path")
    if not document_path or not Path(document_path).exists():
        raise HTTPException(status_code=404, detail="Document not found")

    filename = Path(document_path).name
    return FileResponse(
        path=document_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{job_id}/respond", response_model=UserResponseResult)
async def respond_to_prompt(job_id: str, request: UserResponse):
    """
    Submit user response to resume an interrupted graph.

    This endpoint is called when the graph requires user input (e.g., for itinerary approval).
    After submitting the response, the client should reconnect to the stream endpoint
    to receive further progress updates.
    """
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.get("awaiting_input"):
        raise HTTPException(
            status_code=400,
            detail="Job is not awaiting user input",
        )

    success = await submit_user_response(job_id, request.response)

    if success:
        return UserResponseResult(
            success=True,
            message="Response received, resuming generation",
            stream_url=f"/api/v1/itinerary/stream/{job_id}",
        )
    else:
        return UserResponseResult(
            success=False,
            message="Failed to submit response. The job may have already completed or timed out.",
        )
