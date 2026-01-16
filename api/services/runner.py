"""
Graph runner service with SSE streaming for real-time progress updates.
"""
import asyncio
import logging
import sys
import os
from datetime import datetime
from enum import Enum
from typing import Any, AsyncGenerator, Dict, Optional, Tuple
from uuid import uuid4

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Set matplotlib backend before any imports that might use it
import matplotlib
matplotlib.use('Agg')

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from src.agent.graph import build_graph
from src.processor.email_processor import send_itinerary_email_sync
from .translations import get_translation

logger = logging.getLogger(__name__)


class ProgressEventType(str, Enum):
    """Types of progress events emitted during generation."""
    JOB_STARTED = "job_started"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    DAY_ORGANIZING = "day_organizing"
    DAY_RESEARCHING = "day_researching"
    ATTRACTION_RESEARCHED = "attraction_researched"
    DOCUMENT_GENERATING = "document_generating"
    DOCUMENT_READY = "document_ready"
    EMAIL_SENDING = "email_sending"
    EMAIL_SENT = "email_sent"
    USER_INPUT_REQUIRED = "user_input_required"
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"


# In-memory job storage (use Redis for production)
jobs: Dict[str, Dict[str, Any]] = {}
job_queues: Dict[str, asyncio.Queue] = {}
job_checkpointers: Dict[str, MemorySaver] = {}
job_thread_ids: Dict[str, str] = {}
job_graphs: Dict[str, Any] = {}


def create_job() -> str:
    """Create a new job and return its ID."""
    job_id = str(uuid4())
    jobs[job_id] = {
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
        "document_path": None,
        "costs_by_currency": None,
        "error": None,
        "language": "en",
        "awaiting_input": False,
        "input_prompt": None,
    }
    job_queues[job_id] = asyncio.Queue()
    return job_id


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Get job by ID."""
    return jobs.get(job_id)


async def emit_event(job_id: str, event_type: ProgressEventType, data: Dict[str, Any]):
    """Emit a progress event to the job's queue."""
    if job_id in job_queues:
        event = {
            "type": event_type.value,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await job_queues[job_id].put(event)


async def get_job_events(job_id: str) -> AsyncGenerator[Dict[str, Any], None]:
    """Async generator that yields events for a job."""
    if job_id not in job_queues:
        return

    queue = job_queues[job_id]

    while True:
        try:
            # Wait for event with timeout
            event = await asyncio.wait_for(queue.get(), timeout=60.0)
            yield event

            # Stop if job is done or awaiting input
            if event["type"] in [
                ProgressEventType.JOB_COMPLETED.value,
                ProgressEventType.JOB_FAILED.value,
                ProgressEventType.USER_INPUT_REQUIRED.value,
            ]:
                break
        except asyncio.TimeoutError:
            # Send keepalive
            yield {"type": "keepalive", "data": {}, "timestamp": datetime.utcnow().isoformat()}


async def submit_user_response(job_id: str, response: str) -> bool:
    """Submit user response to resume an interrupted graph."""
    if job_id not in jobs:
        return False

    job = jobs[job_id]
    if not job.get("awaiting_input"):
        return False

    # Mark as no longer awaiting input
    job["awaiting_input"] = False
    job["input_prompt"] = None

    # Get the stored graph and thread_id
    if job_id not in job_graphs or job_id not in job_thread_ids:
        return False

    graph = job_graphs[job_id]
    thread_id = job_thread_ids[job_id]
    checkpointer = job_checkpointers.get(job_id)

    if not checkpointer:
        return False

    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 1000,
    }

    language = job.get("language", "en")
    email = job.get("email")
    send_email = job.get("send_email", False)
    attractions = job.get("attractions", "")
    num_days = job.get("num_days", 1)

    # Resume the graph with user response
    asyncio.create_task(_resume_graph_execution(
        job_id, graph, config, response, language, email, send_email, attractions, num_days
    ))

    return True


async def _resume_graph_execution(
    job_id: str,
    graph: Any,
    config: Dict[str, Any],
    user_response: str,
    language: str,
    email: Optional[str],
    send_email: bool,
    attractions: str,
    num_days: int,
):
    """Resume graph execution after user input."""
    try:
        logger.info(f"Resuming graph execution for job {job_id} with response: {user_response}")

        final_state = None

        # Day organizer is still running - let _process_updates emit STEP_COMPLETED
        # when the node actually finishes (don't pre-add to seen_nodes)
        seen_nodes = set()

        # Check if user approved (response is "yes" or similar)
        is_approved = user_response.lower().strip() in ["yes", "y", "sim", "sí", "oui", "ok", "approve", "approved"]

        # Resume with user's response, updating state to mark approval status
        resume_update = {"itinerary_approved": is_approved}
        if not is_approved:
            resume_update["user_feedback"] = user_response

        async for chunk in graph.astream(
            Command(resume=user_response, update=resume_update),
            config=config,
            stream_mode=["updates", "values"],
        ):
            mode, data = chunk

            if mode == "updates":
                final_state = await _process_updates(job_id, data, seen_nodes, language)

                # Check if we're now awaiting input (hit another interrupt)
                if jobs[job_id].get("awaiting_input"):
                    return  # Exit, will resume with another /respond call

            elif mode == "values":
                final_state = data

        # Process final state (only if not awaiting input)
        if not jobs[job_id].get("awaiting_input"):
            await _process_final_state(
                job_id, final_state, language, email, send_email, attractions, num_days
            )

    except Exception as e:
        logger.exception(f"Error resuming graph for job {job_id}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        await emit_event(job_id, ProgressEventType.JOB_FAILED, {
            "error": str(e),
        })


async def _process_updates(
    job_id: str,
    data: Dict[str, Any],
    seen_nodes: set,
    language: str,
) -> Optional[Dict[str, Any]]:
    """Process node updates and emit progress events."""
    final_state = None

    for node_name, node_output in data.items():
        # Check for interrupt
        if node_name == "__interrupt__":
            interrupt_data = node_output
            # Handle both list and tuple (LangGraph may return either)
            if isinstance(interrupt_data, (list, tuple)) and len(interrupt_data) > 0:
                interrupt_info = interrupt_data[0]
                if hasattr(interrupt_info, 'value'):
                    interrupt_value = interrupt_info.value
                    if isinstance(interrupt_value, dict) and interrupt_value.get("type") == "itinerary_approval":
                        # Store that we're awaiting input
                        jobs[job_id]["awaiting_input"] = True
                        jobs[job_id]["input_prompt"] = interrupt_value

                        await emit_event(job_id, ProgressEventType.USER_INPUT_REQUIRED, {
                            "type": "itinerary_approval",
                            "itinerary": interrupt_value.get("itinerary", ""),
                            "message": get_translation(language, "approval_prompt"),
                        })
            continue

        # Track node transitions for progress
        # NOTE: In LangGraph, updates arrive when nodes COMPLETE, not when they start
        if node_name == "day_organizer_node" and node_name not in seen_nodes:
            seen_nodes.add(node_name)
            # Day organizer FINISHED - emit completion + start researcher
            await emit_event(job_id, ProgressEventType.STEP_COMPLETED, {
                "step": "day_organizer",
                "message": get_translation(language, "attractions_organized"),
            })
            await emit_event(job_id, ProgressEventType.DAY_RESEARCHING, {
                "step": "attraction_researcher",
                "message": get_translation(language, "agent2_researching"),
            })

        elif node_name == "attraction_researcher_node" and "attraction_researcher" not in seen_nodes:
            seen_nodes.add("attraction_researcher")
            # Researcher FINISHED - emit completion + start document
            await emit_event(job_id, ProgressEventType.STEP_COMPLETED, {
                "step": "attraction_researcher",
                "message": get_translation(language, "all_researched"),
            })
            await emit_event(job_id, ProgressEventType.DOCUMENT_GENERATING, {
                "step": "build_document",
                "message": get_translation(language, "generating_document"),
            })

        elif node_name == "build_document_node" and node_name not in seen_nodes:
            seen_nodes.add(node_name)
            # Document FINISHED - completion handled in _process_final_state

        # Capture state from node output if it has the expected fields
        if isinstance(node_output, dict) and "final_document_path" in node_output:
            final_state = node_output

    return final_state


async def _process_final_state(
    job_id: str,
    final_state: Optional[Dict[str, Any]],
    language: str,
    email: Optional[str],
    send_email: bool,
    attractions: str,
    num_days: int,
):
    """Process the final state after graph execution."""
    if final_state is None:
        # Check if we're awaiting input (not an error)
        if jobs[job_id].get("awaiting_input"):
            return

        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = "No final state received"
        await emit_event(job_id, ProgressEventType.JOB_FAILED, {
            "error": get_translation(language, "error_no_state"),
        })
        return

    # Check result
    if final_state.get("invalid_input"):
        error_message = final_state.get("error_message", "Invalid input")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = error_message
        await emit_event(job_id, ProgressEventType.JOB_FAILED, {
            "error": error_message,
        })
        return

    if final_state.get("final_document_path"):
        document_path = final_state["final_document_path"]
        costs = final_state.get("costs_by_currency", {})

        jobs[job_id]["document_path"] = document_path
        jobs[job_id]["costs_by_currency"] = costs

        await emit_event(job_id, ProgressEventType.DOCUMENT_READY, {
            "document_path": document_path,
            "costs": costs,
        })

        # Send email if requested
        if send_email and email:
            logger.info(f"Attempting to send email to {email}")
            logger.info(f"Document path: {document_path}")

            await emit_event(job_id, ProgressEventType.EMAIL_SENDING, {
                "email": email,
                "message": get_translation(language, "sending_email", email=email),
            })

            destination = final_state.get("document_title", "")
            if not destination:
                destination = attractions.split("\n")[0][:30]

            try:
                result = send_itinerary_email_sync(
                    document_path=document_path,
                    to_emails=[email],
                    destination=destination,
                    num_days=num_days,
                    language=language,
                )

                logger.info(f"Email send result: {result}")

                if result.get("success"):
                    await emit_event(job_id, ProgressEventType.EMAIL_SENT, {
                        "success": True,
                        "email": email,
                    })
                else:
                    await emit_event(job_id, ProgressEventType.EMAIL_SENT, {
                        "success": False,
                        "email": email,
                        "error": result.get("error", "Unknown error"),
                    })
            except Exception as e:
                logger.exception(f"Error sending email: {e}")
                await emit_event(job_id, ProgressEventType.EMAIL_SENT, {
                    "success": False,
                    "email": email,
                    "error": str(e),
                })

    # Job completed
    jobs[job_id]["status"] = "completed"
    await emit_event(job_id, ProgressEventType.JOB_COMPLETED, {
        "job_id": job_id,
        "document_path": jobs[job_id].get("document_path"),
        "costs": jobs[job_id].get("costs_by_currency"),
    })


async def run_graph_with_streaming(
    job_id: str,
    attractions: str,
    preferences: str,
    num_days: int,
    language: str,
    email: Optional[str] = None,
    send_email: bool = False,
):
    """Run the LangGraph workflow with progress streaming."""

    try:
        # Update job status and store parameters for potential resume
        jobs[job_id]["status"] = "running"
        jobs[job_id]["language"] = language
        jobs[job_id]["email"] = email
        jobs[job_id]["send_email"] = send_email
        jobs[job_id]["attractions"] = attractions
        jobs[job_id]["num_days"] = num_days

        # Create checkpointer for interrupt/resume support
        checkpointer = MemorySaver()
        job_checkpointers[job_id] = checkpointer

        thread_id = str(uuid4())
        job_thread_ids[job_id] = thread_id

        # Build graph with checkpointer for interrupt support
        graph = build_graph(checkpointer=checkpointer)
        job_graphs[job_id] = graph

        # Emit: Job started (initialization complete)
        await emit_event(job_id, ProgressEventType.JOB_STARTED, {
            "job_id": job_id,
            "num_days": num_days,
            "language": language,
        })

        # Initial state (with api_mode=True to bubble interrupts up to graph level)
        initial_state = {
            "user_input": attractions,
            "num_days": num_days,
            "preferences_input": preferences,
            "language": language,
            "document_title": "",
            "attractions_by_day": [],
            "processed_attractions": [],
            "clusters": [],
            "attraction_coordinates": {},
            "final_document_path": "",
            "costs_by_currency": {},
            "invalid_input": False,
            "error_message": "",
            "organized_days": {},
            "has_flexible_attractions": False,
            "itinerary_approved": False,
            "user_feedback": "",
            "api_mode": True,  # Enable API mode - interrupts bubble up to web UI
        }

        config = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": 1000,
        }

        # Emit: Day organizer starting
        await emit_event(job_id, ProgressEventType.DAY_ORGANIZING, {
            "step": "day_organizer",
            "message": get_translation(language, "organizing_attractions"),
        })

        # Track which nodes we've seen
        seen_nodes = set()
        final_state = None

        # Stream graph execution using astream with multiple modes
        # This captures both updates AND final state without re-running the graph
        async for chunk in graph.astream(
            initial_state,
            config=config,
            stream_mode=["updates", "values"],
        ):
            mode, data = chunk

            if mode == "updates":
                result = await _process_updates(job_id, data, seen_nodes, language)
                if result:
                    final_state = result

                # Check if we're now awaiting input (interrupted)
                if jobs[job_id].get("awaiting_input"):
                    return  # Exit, will resume later

            elif mode == "values":
                # Capture the latest state - this will be the final state at the end
                final_state = data

        # Process final state (only if not awaiting input)
        if not jobs[job_id].get("awaiting_input"):
            await _process_final_state(
                job_id, final_state, language, email, send_email, attractions, num_days
            )

    except Exception as e:
        logger.exception(f"Error in graph execution for job {job_id}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        await emit_event(job_id, ProgressEventType.JOB_FAILED, {
            "error": str(e),
        })
        raise
