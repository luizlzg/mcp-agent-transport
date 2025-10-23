import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Try to import the agent, but don't fail if it's not available
try:
    from agent.graph import TransportationAgent
    agent_available = True
except (ImportError, ValueError) as e:
    TransportationAgent = None
    agent_available = False
    AGENT_ERROR = str(e)


# Initialize FastAPI app
app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize the agent
agent = None
if agent_available:
    try:
        model_provider = None
        if os.getenv("OPENAI_API_KEY"):
            model_provider = "openai"
            model_name = "gpt-4"
        elif os.getenv("ANTHROPIC_API_KEY"):
            model_provider = "anthropic"
            model_name = "claude-sonnet-4-5-20250929"

        if model_provider:
            agent = TransportationAgent(
                model_provider=model_provider,
                model_name=model_name
            )
        else:
            agent = None
            AGENT_ERROR = "No LLM API key configured"

    except Exception as e:
        agent = None
        AGENT_ERROR = str(e)


# Pydantic model for chat requests
class ChatRequest(BaseModel):
    message: str
    thread_id: str

@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    with open("static/index.html") as f:
        return HTMLResponse(content=f.read(), status_code=200)

@app.post("/chat")
async def chat(request: ChatRequest):
    """Endpoint to interact with the agent."""
    if agent is None:
        return {"error": f"Agent not available: {AGENT_ERROR}"}

    try:
        response = agent.chat(request.message, thread_id=request.thread_id)
        return {"response": response}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)