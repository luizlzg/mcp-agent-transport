# Developer Guide

Guide for developers who want to understand, extend, or customize the European Transportation AI Agent.

## Architecture Deep Dive

### Agent Flow

```
User Input
    ↓
[LangGraph State Machine]
    ↓
[Agent Node] ← System Prompt + Conversation History
    ↓
LLM decides: Need tools? Or respond?
    ↓
    ├─→ [Tool Node] → Execute tool(s) → Back to Agent Node
    └─→ [END] → Return response to user
```

### State Management

LangGraph maintains conversation state using:
- **messages**: List of all conversation messages
- **thread_id**: Conversation identifier for memory

### Tool Execution

1. LLM determines which tools to call based on user query
2. Tools are called in parallel when possible
3. Results are fed back to the LLM
4. LLM synthesizes results into user-friendly response

## Code Structure

### 1. Agent Core (`agent/graph.py`)

**Key Components:**

```python
class TransportationAgent:
    def __init__(self, model_provider, model_name)
        # Initializes LLM and builds the graph

    def _build_graph(self):
        # Creates the LangGraph state machine
        # - Agent node: LLM reasoning
        # - Tool node: Tool execution
        # - Conditional edges: Decide next step

    def chat(self, message, thread_id):
        # Synchronous chat
        # Returns complete response

    def stream_chat(self, message, thread_id):
        # Streaming chat
        # Yields response chunks
```

**Graph Structure:**

```python
workflow = StateGraph(AgentState)

# Nodes
workflow.add_node("agent", agent_node)    # LLM reasoning
workflow.add_node("tools", tool_node)     # Tool execution

# Edges
workflow.add_edge(START, "agent")         # Start → Agent
workflow.add_conditional_edges("agent", tools_condition)  # Agent → Tools or END
workflow.add_edge("tools", "agent")       # Tools → Agent (loop)
```

### 2. Tools (`agent/tools.py`)

**Tool Definition Pattern:**

```python
@tool
def search_flights(origin: str, destination: str, departure_date: str) -> str:
    """
    Docstring becomes tool description for LLM.

    Args are automatically parsed and validated.

    Returns:
        JSON string (LLMs work best with structured text)
    """
    # 1. Call API
    # 2. Process results
    # 3. Return JSON string
```

**Available Tools:**

1. `search_flights` - Amadeus API
2. `search_trains` - SNCF API
3. `search_buses` - FlixBus API
4. `search_all_transport` - All three in parallel
5. `save_itinerary` - Save to file
6. `load_itinerary` - Load from file
7. `list_saved_itineraries` - List all saved

### 3. API Clients (`apis/`)

**Pattern for all API clients:**

```python
class APIClient:
    def __init__(self):
        # Load API keys from environment
        self.api_key = os.getenv('API_KEY')

    def search(self, origin, destination, date):
        # 1. Call API
        # 2. Handle errors
        # 3. Parse response
        # 4. Return standardized format

    def _parse_response(self, response):
        # Convert API response to standard format
        return {
            'type': 'flight|train|bus',
            'provider': 'Provider name',
            'price': float,
            'currency': 'EUR',
            'duration': 'PT2H30M',
            'departure_time': 'ISO 8601',
            'arrival_time': 'ISO 8601',
            # ... more fields
        }
```

**Standard Response Format:**

All transportation APIs return this format:

```python
{
    'type': 'flight' | 'train' | 'bus',
    'provider': str,
    'price': float | None,
    'currency': str,
    'duration': str,  # ISO 8601 duration
    'departure_time': str,  # ISO 8601 datetime
    'arrival_time': str,
    'origin': str,
    'destination': str,
    'stops': int,  # flights
    'transfers': int,  # trains/buses
    'details': dict  # provider-specific data
}
```

### 4. MCP Client (`mcp/client.py`)

Two implementations:

1. **MCPFilesystemClient** - Async MCP (if available)
2. **SimplifiedFilesystemTools** - Fallback synchronous

Currently uses SimplifiedFilesystemTools for simplicity.

## Adding a New Transportation API

### Step 1: Create API Client

```python
# apis/newapi.py

import os
import requests
from typing import List, Dict

class NewTransportAPI:
    def __init__(self):
        self.api_key = os.getenv('NEWAPI_KEY')
        self.base_url = "https://api.example.com"

    def search(self, origin: str, destination: str, date: str) -> List[Dict]:
        """Search for transport options."""
        try:
            response = requests.get(
                f"{self.base_url}/search",
                params={'from': origin, 'to': destination, 'date': date},
                headers={'Authorization': f'Bearer {self.api_key}'}
            )
            response.raise_for_status()

            data = response.json()
            return [self._parse(item) for item in data['results']]

        except Exception as e:
            print(f"Error: {e}")
            return []

    def _parse(self, item: Dict) -> Dict:
        """Parse API response to standard format."""
        return {
            'type': 'newtype',
            'provider': 'NewProvider',
            'price': item['price'],
            'currency': item['currency'],
            'duration': item['duration'],
            # ... map all fields
        }
```

### Step 2: Create Tool

```python
# agent/tools.py

from apis.newapi import NewTransportAPI

newapi = NewTransportAPI()

@tool
def search_newtransport(
    origin: str,
    destination: str,
    departure_date: str
) -> str:
    """
    Search for [transport type] between two cities.

    Args:
        origin: Origin city
        destination: Destination city
        departure_date: Date in YYYY-MM-DD format

    Returns:
        JSON string with options
    """
    try:
        results = newapi.search(origin, destination, departure_date)

        if not results:
            return json.dumps({
                "message": "No results found",
                "note": "Set NEWAPI_KEY in .env"
            })

        return json.dumps({
            "count": len(results),
            "options": results
        }, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)})

# Add to ALL_TOOLS
ALL_TOOLS.append(search_newtransport)
```

### Step 3: Update Documentation

1. Add to `.env.example`:
   ```
   NEWAPI_KEY=your_key
   ```

2. Update `API_DOCUMENTATION.md` with:
   - Signup process
   - Pricing
   - Rate limits
   - Example usage

3. Update `SETUP_GUIDE.md` with setup instructions

## Customizing Agent Behavior

### Modify System Prompt

Edit `agent/prompts.py`:

```python
SYSTEM_PROMPT = """
Your custom instructions here...

Examples:
- Always prioritize eco-friendly options
- Consider CO2 emissions
- Suggest overnight trains when possible
"""
```

### Add Custom Logic

Modify the agent node in `agent/graph.py`:

```python
def agent_node(state: AgentState):
    """Agent reasoning node."""
    messages = state["messages"]

    # Custom logic before LLM call
    # Example: Add context about user preferences

    # Add system message
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages

    # Invoke LLM
    response = llm_with_tools.invoke(messages)

    # Custom logic after LLM call
    # Example: Filter or modify response

    return {"messages": [response]}
```

### Implement Memory

Store user preferences:

```python
# Simple in-memory storage
user_preferences = {}

@tool
def save_preference(preference_key: str, preference_value: str) -> str:
    """Save a user preference."""
    user_preferences[preference_key] = preference_value
    return json.dumps({"status": "saved"})

@tool
def get_preferences() -> str:
    """Get user preferences."""
    return json.dumps(user_preferences)
```

## Testing

### Unit Tests

Create `tests/test_apis.py`:

```python
import unittest
from apis.amadeus import AmadeusFlightAPI

class TestAmadeusAPI(unittest.TestCase):
    def setUp(self):
        self.api = AmadeusFlightAPI()

    def test_search_flights(self):
        results = self.api.search_flights(
            origin="PAR",
            destination="BER",
            departure_date="2025-11-15"
        )
        self.assertIsInstance(results, list)

    def test_get_iata_code(self):
        code = self.api.get_city_iata_code("Paris")
        self.assertEqual(code, "PAR")
```

### Integration Tests

Test the full agent:

```python
from agent.graph import TransportationAgent

def test_agent_search():
    agent = TransportationAgent(
        model_provider="openai",
        model_name="gpt-4"
    )

    response = agent.chat(
        "Find flights from Paris to Berlin on 2025-11-15"
    )

    assert "flight" in response.lower()
    assert "paris" in response.lower()
    assert "berlin" in response.lower()
```

## Performance Optimization

### 1. Caching

Add response caching:

```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=100)
def cached_flight_search(origin, destination, date):
    # Cache key based on parameters
    return flight_api.search_flights(origin, destination, date)
```

### 2. Parallel API Calls

Already implemented in `search_all_transport`:

```python
import concurrent.futures

def search_all_parallel(origin, destination, date):
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        future_flights = executor.submit(search_flights, origin, destination, date)
        future_trains = executor.submit(search_trains, origin, destination, date)
        future_buses = executor.submit(search_buses, origin, destination, date)

        results = []
        results.extend(future_flights.result())
        results.extend(future_trains.result())
        results.extend(future_buses.result())

        return results
```

### 3. Rate Limiting

Implement rate limiter:

```python
import time
from collections import deque

class RateLimiter:
    def __init__(self, max_calls, time_window):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = deque()

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            now = time.time()

            # Remove old calls
            while self.calls and self.calls[0] < now - self.time_window:
                self.calls.popleft()

            # Check limit
            if len(self.calls) >= self.max_calls:
                sleep_time = self.time_window - (now - self.calls[0])
                time.sleep(sleep_time)

            # Make call
            self.calls.append(time.time())
            return func(*args, **kwargs)

        return wrapper

# Usage
@RateLimiter(max_calls=10, time_window=60)  # 10 calls per minute
def api_call():
    pass
```

## Deployment

### Docker

Create `Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

### Environment Variables

Use python-dotenv or container secrets:

```python
import os
from pathlib import Path
from dotenv import load_dotenv

# Load from multiple sources
load_dotenv()  # .env file
load_dotenv(Path("/run/secrets/api_keys"))  # Docker secrets
```

### Web API (FastAPI)

Create `api.py`:

```python
from fastapi import FastAPI
from pydantic import BaseModel
from agent.graph import TransportationAgent

app = FastAPI()
agent = TransportationAgent()

class SearchRequest(BaseModel):
    origin: str
    destination: str
    date: str

@app.post("/search")
async def search(request: SearchRequest):
    response = agent.chat(
        f"Find transport from {request.origin} to {request.destination} "
        f"on {request.date}"
    )
    return {"response": response}
```

## Debugging

### Enable Verbose Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)

# LangChain logging
from langchain.globals import set_debug
set_debug(True)
```

### Inspect Agent State

```python
# In agent/graph.py
def agent_node(state: AgentState):
    print(f"State: {state}")  # Debug print
    print(f"Messages: {len(state['messages'])}")

    # ... rest of code
```

### Test Individual Tools

```python
from agent.tools import search_flights

result = search_flights.invoke({
    "origin": "Paris",
    "destination": "Berlin",
    "departure_date": "2025-11-15"
})

print(result)
```

## Common Patterns

### Error Handling

```python
@tool
def safe_search(origin: str, destination: str, date: str) -> str:
    try:
        # Attempt search
        results = api.search(origin, destination, date)

        if not results:
            return json.dumps({
                "status": "no_results",
                "suggestion": "Try different dates or cities"
            })

        return json.dumps({"status": "success", "results": results})

    except ConnectionError:
        return json.dumps({
            "status": "error",
            "message": "API temporarily unavailable",
            "retry": True
        })

    except ValueError as e:
        return json.dumps({
            "status": "error",
            "message": f"Invalid input: {str(e)}",
            "retry": False
        })
```

### Validation

```python
from datetime import datetime
from pydantic import BaseModel, validator

class SearchParams(BaseModel):
    origin: str
    destination: str
    date: str

    @validator('date')
    def validate_date(cls, v):
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('Date must be in YYYY-MM-DD format')

    @validator('origin', 'destination')
    def validate_city(cls, v):
        if len(v) < 2:
            raise ValueError('City name too short')
        return v.title()
```

## Best Practices

1. **Always return JSON from tools** - LLMs parse structured data better
2. **Include helpful error messages** - Guide the LLM on how to recover
3. **Use type hints** - Makes code self-documenting
4. **Cache expensive calls** - Reduce API costs
5. **Handle rate limits gracefully** - Use exponential backoff
6. **Test with real data** - Don't rely on mocks for APIs
7. **Log everything** - Helps debug agent decisions
8. **Keep prompts concise** - Token costs add up

## Resources

- LangChain Docs: https://python.langchain.com/
- LangGraph Docs: https://langchain-ai.github.io/langgraph/
- ReAct Paper: https://arxiv.org/abs/2210.03629
- MCP Spec: https://github.com/modelcontextprotocol/

---

Happy coding! If you build something cool, consider contributing back.
