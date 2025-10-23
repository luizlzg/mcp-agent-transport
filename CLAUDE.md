# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **LangGraph ReAct agent** built with **LangChain 1.0** that finds European transportation routes (flights, trains, buses) using real API integrations. It's a production-ready MVP with no mock data.

**Core Technologies:**
- LangChain 1.0 (langchain>=1.0.0, langchain-core>=1.0.0) - **IMPORTANT: v1.0 compliant**
- LangGraph for state machine orchestration
- Python 3.10+ (required by LangChain 1.0)
- Real APIs: Amadeus (flights), SNCF (trains), FlixBus (buses)
- MCP (Model Context Protocol) for filesystem operations

## Essential Commands

### Setup and Installation
```bash
# Install dependencies (requires Python 3.10+)
pip install -r requirements.txt

# Run the interactive agent
python main.py

# Run test suite (verifies setup, API keys, agent initialization)
python test_agent.py
```

### Environment Configuration
```bash
# Minimum required: LLM API key
echo "OPENAI_API_KEY=sk-..." > .env

# Full configuration (see .env.example for all options)
cp .env.example .env
# Edit .env to add: AMADEUS_API_KEY, AMADEUS_API_SECRET, RAPIDAPI_KEY, SNCF_API_KEY
```

### Testing Individual Components
```bash
# Test a specific API client
python -c "from apis.amadeus import AmadeusFlightAPI; api = AmadeusFlightAPI(); print(api.search_flights('PAR', 'BER', '2025-11-15'))"

# Test agent tools
python -c "from agent.tools import search_flights; print(search_flights.invoke({'origin': 'Paris', 'destination': 'Berlin', 'departure_date': '2025-11-15'}))"

# Test agent initialization
python -c "from agent.graph import TransportationAgent; agent = TransportationAgent(); print('Agent ready')"
```

## Architecture: Critical Components

### 1. LangGraph State Machine (`agent/graph.py`)

**Key Implementation Detail - LangChain 1.0 Compliance:**
- **MUST use TypedDict** for state (not Pydantic models or dataclasses)
- State definition: `AgentState(TypedDict)` with `messages: Annotated[list, add_messages]`
- Custom graph implementation (doesn't use deprecated `create_react_agent`)

**Graph Flow:**
```
START → agent_node (LLM reasoning) → tools_condition → [tools_node OR END]
                ↑                                            ↓
                └────────────── (loop back) ─────────────────┘
```

The agent node:
1. Binds tools to LLM: `llm_with_tools = self.llm.bind_tools(ALL_TOOLS)`
2. Prepends system prompt if not present
3. Invokes LLM which decides: call tools OR respond
4. Returns updated messages

**Critical:** The conditional edge uses `tools_condition` from LangGraph to determine if LLM wants to call tools or end conversation.

### 2. Tool Layer (`agent/tools.py`)

**Tool Pattern:**
- All tools use `@tool` decorator from `langchain_core.tools`
- **MUST return JSON strings** (not dicts) - LLMs parse structured text better
- Tools invoke API clients and return standardized responses

**Available Tools:**
1. `search_flights` - Amadeus API (converts city names to IATA codes) - Use `search_all_transport` instead
2. `search_trains` - SNCF API (Navitia endpoint) - Use `search_all_transport` instead
3. `search_buses` - FlixBus via RapidAPI - Use `search_all_transport` instead
4. `search_all_transport` - **PRIMARY TOOL**: Searches all transport types (flights + trains + buses) simultaneously
5. `analyze_best_routes` - Identifies cheapest and fastest from single-leg results, shows discarded options with reasoning
6. `optimize_multi_city_route` - **Multi-city TSP optimizer**: Finds best ORDER to visit 3+ cities, tests all permutations
7. `save_itinerary` - Save itineraries using MCP filesystem
8. `load_itinerary` - Load saved searches via MCP
9. `list_saved_itineraries` - List all saved files via MCP

**Standardized Response Format** (all transportation tools):
```python
{
    'type': 'flight' | 'train' | 'bus',
    'provider': str,
    'price': float | None,
    'currency': str,
    'duration': str,  # ISO 8601 (e.g., 'PT2H30M')
    'departure_time': str,  # ISO 8601
    'arrival_time': str,
    'origin': str,
    'destination': str,
    'stops': int,  # flights
    'transfers': int,  # trains/buses
    'details': dict
}
```

### 3. API Client Pattern (`apis/`)

All API clients follow the same structure:
```python
class APIClient:
    def __init__(self):
        self.api_key = os.getenv('API_KEY')  # Load from environment

    def search(self, origin, destination, date) -> List[Dict]:
        # 1. Call external API
        # 2. Handle errors gracefully (return [] on failure)
        # 3. Parse to standardized format
        return [self._parse(item) for item in results]

    def _parse(self, item) -> Dict:
        # Convert API-specific format to standard format
```

**API-Specific Notes:**
- **Amadeus** (`apis/amadeus.py`): Uses `amadeus` package, requires OAuth (API key + secret)
- **SNCF** (`apis/trains.py`): Uses Navitia API, may not return prices for all routes
- **FlixBus** (`apis/buses.py`): Via RapidAPI, requires station ID lookup before trip search

### 4. Route Analysis Tool (`agent/tools.py` - `analyze_best_routes`)

**NEW Feature**: Automatically identifies the cheapest and fastest options from search results.

**How it works:**
1. Takes all transportation options as JSON input
2. Identifies the option with the lowest price (cheapest)
3. Identifies the option with shortest duration (fastest)
4. For all other options, calculates and explains why they were discarded
5. Returns structured JSON with:
   - `recommended.cheapest` - The cheapest option
   - `recommended.fastest` - The fastest option
   - `discarded` - Array of rejected options with reasons (e.g., "30.00 EUR more expensive", "2h 15m slower")

**Agent Behavior:**
- The system prompt instructs the agent to ALWAYS use this tool after searching
- Agent MUST present both recommended AND discarded options to the user
- This provides transparency in decision-making and helps users understand trade-offs

### 5. MCP Filesystem Integration (`mcp_client/client.py`)

**Architecture:**
- Uses `MCPFilesystemClient` for async MCP operations
- Filesystem tools (`save_itinerary`, `load_itinerary`, `list_saved_itineraries`) wrap async MCP calls
- Helper function `run_async_mcp_operation()` bridges async MCP with synchronous LangChain tools
- MCP server runs via `npx @modelcontextprotocol/server-filesystem`

**Why MCP:**
- Standard protocol for LLM filesystem access
- Sandboxed operations in `./saved_itineraries` directory
- Better security than direct filesystem access
- Async operations for better performance

### 6. Multi-City Route Optimization (`agent/tools.py` - `optimize_multi_city_route`)

Solves the **Traveling Salesman Problem** for multi-city trips.

**Use Case:** User wants to visit Paris, Madrid, Berlin → Find best ORDER to visit them

**How it works:**
1. Generates all permutations (3 cities = 6 routes, 4 cities = 24 routes)
2. For each route order, searches all transport for each leg using cheapest option
3. Returns cheapest and fastest complete route ORDER
4. Shows why other route orders were discarded (e.g., "30 EUR more expensive", "5h slower")

**Example:**
- Input: ["Paris", "Madrid", "Berlin"]
- Output: Cheapest = Madrid→Paris→Berlin (180 EUR), Fastest = Paris→Berlin→Madrid (6.5h)
- Discarded: 4 other route orders with specific reasons

### 7. System Prompts (`agent/prompts.py`)

Contains:
- `SYSTEM_PROMPT` - Main agent instructions (MUST use search_all_transport and analyze_best_routes for single routes, optimize_multi_city_route for 3+ cities)
- `format_duration()` - Converts ISO 8601 to human-readable (e.g., "2 hours 30 minutes")
- `format_transport_option()` - Formats results for display

## Critical LangChain 1.0 Requirements

When modifying agent code, you **MUST**:

1. **Use TypedDict for state** - Pydantic models are not supported in v1.0
   ```python
   # ✅ CORRECT
   class AgentState(TypedDict):
       messages: Annotated[list, add_messages]

   # ❌ WRONG - will fail with v1.0
   class AgentState(BaseModel):
       messages: list
   ```

2. **Python 3.10+** - v1.0 dropped Python 3.9 support

3. **Don't use deprecated imports**:
   - ❌ `from langgraph.prebuilt import create_react_agent`
   - ✅ Build custom graph with `StateGraph` (as we do)

4. **Return AIMessage type** (not BaseMessage) from chat models

See `LANGCHAIN_1.0_NOTES.md` for complete v1.0 compliance details.

## Adding a New Transportation API

**Step 1:** Create API client in `apis/newapi.py`
```python
class NewTransportAPI:
    def __init__(self):
        self.api_key = os.getenv('NEWAPI_KEY')

    def search(self, origin, destination, date) -> List[Dict]:
        # Implement API call
        # Return standardized format (see Tool Layer section above)
```

**Step 2:** Create tool in `agent/tools.py`
```python
@tool
def search_newtransport(origin: str, destination: str, departure_date: str) -> str:
    """Docstring becomes tool description for LLM."""
    results = newapi.search(origin, destination, departure_date)
    return json.dumps({"count": len(results), "options": results})

# Add to ALL_TOOLS list at bottom of file
ALL_TOOLS.append(search_newtransport)
```

**Step 3:** Update documentation:
- Add `NEWAPI_KEY` to `.env.example`
- Document in `API_DOCUMENTATION.md` (signup, pricing, rate limits)
- Update `SETUP_GUIDE.md` with setup instructions

## Common Pitfalls to Avoid

1. **Don't change state schema to Pydantic** - Must use TypedDict for LangChain 1.0
2. **Don't return dicts from tools** - Always return JSON strings
3. **Don't forget error handling in API clients** - Return empty list `[]` on failure, not exceptions
4. **Don't hardcode API keys** - Always use `os.getenv()` with `.env` file
5. **Don't use Python 3.9** - LangChain 1.0 requires 3.10+

## File Organization

```
agent/
  graph.py          # LangGraph state machine (START → agent → tools → agent → END)
  tools.py          # All 7 agent tools with @tool decorator
  prompts.py        # System prompts and formatting utilities

apis/
  amadeus.py        # Flight API client (Amadeus SDK)
  trains.py         # Train API client (SNCF/Navitia)
  buses.py          # Bus API client (FlixBus via RapidAPI)

mcp/
  client.py         # MCP filesystem client (currently uses SimplifiedFilesystemTools)

main.py             # Entry point - Rich CLI interface
test_agent.py       # Test suite (imports, API keys, clients, tools, agent)
```

## Debugging Tips

**Enable LangChain debug mode:**
```python
from langchain.globals import set_debug
set_debug(True)
```

**Test individual components:**
```python
# Test API client directly
from apis.amadeus import AmadeusFlightAPI
api = AmadeusFlightAPI()
results = api.search_flights("PAR", "BER", "2025-11-15")

# Test tool invocation
from agent.tools import search_flights
result = search_flights.invoke({
    "origin": "Paris",
    "destination": "Berlin",
    "departure_date": "2025-11-15"
})
```

**Check agent state:**
Add debug prints in `agent/graph.py` agent_node:
```python
def agent_node(state: AgentState):
    print(f"DEBUG: State has {len(state['messages'])} messages")
    # ... rest of code
```

## Key Design Decisions

1. **Custom graph over prebuilt agent** - Provides full control and avoids v1.0 import changes
2. **JSON string returns from tools** - LLMs parse structured text better than Python objects
3. **SimplifiedFilesystemTools over async MCP** - Simpler for CLI usage, can upgrade to async later
4. **Standardized response format** - All transportation APIs return same schema for consistency
5. **Graceful API failures** - Return empty results rather than crashing, let agent handle missing data

## Reference Documentation

- `PROJECT_OVERVIEW.md` - High-level architecture and design decisions
- `DEVELOPER_GUIDE.md` - Detailed implementation patterns and examples
- `LANGCHAIN_1.0_NOTES.md` - Complete v1.0 compliance guide
- `API_DOCUMENTATION.md` - API signup, pricing, rate limits, troubleshooting
- `SETUP_GUIDE.md` - Step-by-step setup with all API keys

## Rules

1. **NEVER create new .md files** - Do not create markdown files to document changes, summarize work, or explain what you did
   - No BUG_FIXES.md, CHANGES_SUMMARY.md, WORKFLOW_UPDATE.md, etc.
   - Only update existing documentation files if absolutely necessary
   - Communicate changes verbally to the user instead

2. **NEVER create test_*.py files** - Do not create temporary test files
   - Use existing test_agent.py for testing
   - Run inline Python tests with `python -c "..."` instead
   - Clean up any test files you create during the session

3. **Keep the repository clean** - Minimize file creation
   - Only create files that are part of the actual application
   - No summary files, analysis files, or documentation of changes
   - User prefers a clean, minimal repository
