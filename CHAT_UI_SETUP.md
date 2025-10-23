# Agent Chat UI Setup

This guide explains how to use the LangChain Agent Chat UI with this transportation agent.

## Overview

The project includes a web-based chat interface powered by [LangChain's Agent Chat UI](https://github.com/langchain-ai/agent-chat-ui). This provides a modern chat interface to interact with the transportation agent through your browser.

## Quick Start

### 1. Start the LangGraph API Server

The LangGraph server exposes the agent through an API that the chat UI connects to.

```bash
# Activate virtual environment
. venv/Scripts/activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Start the dev server
langgraph dev
```

The server will start at:
- API: `http://127.0.0.1:2024`
- API Docs: `http://127.0.0.1:2024/docs`
- Studio UI: `https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024`

### 2. Access the Chat UI

You have two options:

#### Option A: Use the Deployed Chat UI (Easiest)

1. Open https://agentchat.vercel.app in your browser
2. Enter the following configuration:
   - **Deployment URL**: `http://localhost:2024`
   - **Assistant/Graph ID**: `agent`
   - **LangSmith API Key**: Leave empty for local development

#### Option B: Run Chat UI Locally

Clone and run the chat UI locally:

```bash
# In a new terminal (keep langgraph dev running)
cd ..
git clone https://github.com/langchain-ai/agent-chat-ui.git
cd agent-chat-ui
pnpm install
pnpm dev
```

Then open `http://localhost:3000` and connect to:
- **API URL**: `http://localhost:2024`
- **Assistant ID**: `agent`

## Features

The Agent Chat UI provides:

- **Real-time chat interface** - Send messages and see responses in real-time
- **Tool call visualization** - See when the agent calls transportation APIs
- **Tool results** - View the data returned from flights, trains, and buses searches
- **Conversation history** - Maintains conversation context across messages
- **Streaming responses** - See the agent's response as it's generated

## Architecture

```
User Browser
    ↓
Agent Chat UI (Next.js)
    ↓
LangGraph API Server (http://localhost:2024)
    ↓
Transportation Agent (Python)
    ↓
External APIs (Amadeus, SNCF, FlixBus)
```

## Configuration Files

### langgraph.json

Defines the graph configuration for the LangGraph API:

```json
{
  "dependencies": ["."],
  "graphs": {
    "agent": "./agent/graph.py:create_graph"
  },
  "env": ".env"
}
```

- **dependencies**: Installs the current package in editable mode
- **graphs**: Maps the graph ID ("agent") to the factory function
- **env**: Loads environment variables from `.env`

### pyproject.toml

Python package configuration required by LangGraph CLI:

```toml
[project]
name = "mcp-agent-transport"
dependencies = [
    "langchain>=1.0.0",
    "langgraph>=1.0.0",
    ...
]
```

## Troubleshooting

### Server won't start

**Error**: `Blocking call to os.getcwd`

**Solution**: The `create_graph()` function in [agent/graph.py](agent/graph.py) should NOT call `load_dotenv()`. Environment variables are loaded by LangGraph API from the `.env` file.

### Chat UI can't connect

1. Verify the LangGraph server is running: `curl http://localhost:2024/assistants/search`
2. Check that port 2024 is not blocked by firewall
3. Ensure `.env` file has valid API keys

### No responses from agent

1. Check that `.env` has either `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`
2. View server logs in the terminal running `langgraph dev`
3. Check API documentation at http://localhost:2024/docs

## Advanced: Environment Variables for Chat UI

If running the chat UI locally, you can bypass the setup form:

```bash
# In agent-chat-ui directory
cp .env.example .env
```

Edit `.env`:
```
NEXT_PUBLIC_API_URL=http://localhost:2024
NEXT_PUBLIC_ASSISTANT_ID=agent
```

## Development Workflow

1. Make changes to agent code in [agent/](agent/) directory
2. LangGraph dev server auto-reloads on file changes
3. Refresh chat UI to use the updated agent
4. Test transportation searches through the chat interface

## Example Conversation

```
You: Find me flights from Paris to Berlin on November 15th

Agent: [Calls search_all_transport tool]
        [Calls analyze_best_routes tool]

        I found several options for traveling from Paris to Berlin on November 15th:

        **Recommended Options:**

        Cheapest: FlixBus - €45.00 (8h 30m)
        - Departure: 10:00 AM
        - Arrival: 6:30 PM
        - 0 transfers

        Fastest: Flight (Lufthansa) - €120.00 (1h 45m)
        - Departure: 2:15 PM
        - Arrival: 4:00 PM
        - Non-stop

        **Other Options:**

        - Train (SNCF) - €89.00 (9h 15m) - €44.00 more expensive than cheapest, 45m slower
        - Flight (Air France) - €135.00 (2h 10m) - €15.00 more expensive than fastest option

        Would you like me to search for a different date or route?
```

## Next Steps

- **Deploy to production**: Use [LangSmith Platform](https://smith.langchain.com) for production deployments
- **Add authentication**: Implement auth in LangGraph deployment for security
- **Custom UI components**: Add generative UI for richer visualizations
- **Multi-user support**: Deploy with proper database checkpointer (not in-memory)

## Related Documentation

- [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) - Project architecture
- [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) - Implementation details
- [API_DOCUMENTATION.md](API_DOCUMENTATION.md) - External API setup
- [LangGraph Platform Docs](https://langchain-ai.github.io/langgraph/)
- [Agent Chat UI Repo](https://github.com/langchain-ai/agent-chat-ui)
