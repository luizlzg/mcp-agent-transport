# European Transport AI Agent

A production-ready LangGraph-based ReAct agent that finds the cheapest and fastest routes between European cities using real-time data from planes, trains, and buses.

![Status](https://img.shields.io/badge/status-MVP-green)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![LangChain](https://img.shields.io/badge/langchain-1.0-purple)
![License](https://img.shields.io/badge/license-MIT-orange)

## Quick Links

- **[Quick Start (5 min)](QUICKSTART.md)** - Get running in 5 minutes
- **[Setup Guide](SETUP_GUIDE.md)** - Detailed installation and configuration
- **[API Documentation](API_DOCUMENTATION.md)** - API keys, pricing, and usage
- **[Project Overview](PROJECT_OVERVIEW.md)** - Architecture and design decisions
- **[LangChain 1.0 Notes](LANGCHAIN_1.0_NOTES.md)** - v1.0 compliance and migration details

## Features

- **Multi-modal Transport Search**: Compares prices and times across flights, trains, and buses
- **Real API Integration** (no mock data):
  - ✈️ Flights: Amadeus API (270+ airlines worldwide)
  - 🚂 Trains: SNCF API (French railways + international)
  - 🚌 Buses: FlixBus API (2,500+ destinations)
- **Interactive Chat Interface**: Natural language queries with clarifying questions
- **Filesystem Integration**: Save and load itineraries via MCP
- **ReAct Architecture**: Intelligent reasoning and acting loop
- **Beautiful CLI**: Rich terminal interface with markdown support

## Tech Stack

- **LangChain 1.0** - Latest stable release (langchain>=1.0.0, langchain-core>=1.0.0)
  - TypedDict state schemas (v1.0 compliant)
  - Modern message handling
  - Improved tool integration
- **LangGraph** - State-based agent orchestration
- **MCP (Model Context Protocol)** - Standardized tool integration
- **Real APIs** - Amadeus, SNCF, FlixBus with live data
- **Python 3.10+** - Required by LangChain 1.0

## How to Run

### Interactive CLI

1.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Set up environment variables:**
    -   Copy `.env.example` to `.env`
    -   Add your API keys (OpenAI/Anthropic, Amadeus, SNCF, RapidAPI)

3.  **Run the agent:**
    ```bash
    python main.py
    ```

### Web Interface

1.  **Ensure all dependencies are installed:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Run the web server:**
    ```bash
    uvicorn server:app --reload
    ```

3.  **Open your browser** and navigate to `http://127.0.0.1:8000`.

## Example Conversation

```
You: I need to go from Paris to Berlin on November 15th

Agent: Let me search for all transportation options for you...

       Here are your options from Paris to Berlin on November 15th:

       1. ✈️  Flight (Ryanair): €129.00 - 2 hours (fastest)
       2. 🚂 Train (SNCF): €89.00 - 8 hours 15 minutes
       3. 🚌 Bus (FlixBus): €45.90 - 13 hours 30 minutes (cheapest)

       The bus is the most economical option, while the flight
       is fastest. Would you like me to save any of these?

You: Save the cheapest option

Agent: ✓ Saved to saved_itineraries/paris_berlin_2025-11-15.json
```

## Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Get up and running in 5 minutes
- **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Complete setup instructions with all API keys
- **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** - Detailed API information, pricing, and troubleshooting
- **[PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)** - Architecture, design decisions, and technical details

## Testing

Run the test suite to verify your setup:

```bash
python test_agent.py
```

This checks:
- ✓ All dependencies installed
- ✓ API keys configured correctly
- ✓ API clients working
- ✓ Agent initializes properly

## Project Structure

```
mcp-agent-transport/
├── main.py                 # Entry point - interactive chat interface
├── test_agent.py          # Test suite for verification
├── requirements.txt       # Python dependencies
├── .env.example          # Environment template
│
├── agent/                # LangGraph ReAct agent
│   ├── graph.py         # Agent state machine and orchestration
│   ├── tools.py         # All agent tools (search, save, etc.)
│   └── prompts.py       # System prompts and formatting
│
├── apis/                 # Real API integrations
│   ├── amadeus.py       # Amadeus flight search
│   ├── trains.py        # SNCF train search
│   └── buses.py         # FlixBus search via RapidAPI
│
├── mcp/                  # Model Context Protocol
│   └── client.py        # MCP filesystem client
│
├── saved_itineraries/   # User-saved searches
│
└── docs/                # Complete documentation
    ├── README.md
    ├── QUICKSTART.md
    ├── SETUP_GUIDE.md
    ├── API_DOCUMENTATION.md
    └── PROJECT_OVERVIEW.md
```

## What Makes This Special

1. **Real MVP**: No mock data - all APIs are production-ready
2. **LangChain 1.0**: Uses the latest LangChain features
3. **Proper ReAct**: True reasoning and acting loop with LangGraph
4. **MCP Integration**: Standardized tool protocol for filesystem
5. **Comprehensive Docs**: Everything you need to deploy
6. **Beautiful UX**: Rich CLI with markdown rendering
7. **Extensible**: Easy to add new APIs or features

## Cost Estimation

**Testing/Development** (10-20 queries/day):
- OpenAI GPT-4: ~$0.50-1.00/day
- APIs: Free (within tier limits)
- **Total: < $1/day**

**Production** (100 queries/day):
- OpenAI GPT-4: ~$5-10/day
- APIs: Free + minimal overage
- **Total: ~$200-300/month**

## Requirements

- Python 3.10 or higher
- OpenAI or Anthropic API key
- (Optional) Transportation API keys for real data
- (Optional) Node.js for MCP servers

## Contributing

This is a complete, working MVP. Areas for enhancement:

1. Add more transportation APIs (Trainline, Deutsche Bahn, etc.)
2. Support multi-city routes
3. Add booking capabilities
4. Build a web interface
5. Implement price tracking and alerts

## License

MIT License - Free to use and modify

## Support

- Run `python test_agent.py` to diagnose issues
- Check [SETUP_GUIDE.md](SETUP_GUIDE.md) for troubleshooting
- Review [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for API help

---

Built with LangChain 1.0 and LangGraph. This is a production-ready MVP with real API integrations.
