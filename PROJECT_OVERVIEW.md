# Project Overview - European Transportation AI Agent

## What This Project Does

An intelligent AI agent built with **LangGraph** and **LangChain 1.0** that helps users find the cheapest and fastest routes between European cities by comparing real-time prices and schedules across:

- ✈️ **Flights** (via Amadeus API)
- 🚂 **Trains** (via SNCF API)
- 🚌 **Buses** (via FlixBus API)

The agent uses a **ReAct (Reasoning and Acting)** architecture to:
1. Ask clarifying questions when information is missing
2. Search multiple transportation APIs in parallel
3. Compare and recommend options based on user preferences
4. Save itineraries for future reference

## Key Features

### 🤖 Intelligent Conversational Agent
- Natural language understanding
- Asks follow-up questions to clarify requirements
- Understands preferences (cheapest vs fastest)
- Provides recommendations with trade-off analysis

### 🌐 Real API Integration
- **Amadeus API**: Real-time flight data from airlines worldwide
- **SNCF API**: French train schedules with real-time updates
- **FlixBus API**: European bus network pricing and schedules
- No mock data - all results are live and bookable

### 💾 Filesystem Integration (MCP)
- Save search results as JSON files
- Load previously saved itineraries
- List all saved searches
- Uses Model Context Protocol for standardized file operations

### ⚡ Modern Tech Stack
- **LangChain 1.0**: Latest version with improved tooling
- **LangGraph**: State machine for agent orchestration
- **ReAct Pattern**: Reasoning and acting loop
- **Streaming Support**: Real-time response streaming
- **Rich CLI**: Beautiful terminal interface

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         User Input                          │
│                    "Paris to Berlin on Nov 15"              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph Agent                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │            ReAct Loop (Reasoning & Acting)           │  │
│  │                                                       │  │
│  │  1. Analyze user request                            │  │
│  │  2. Determine needed information                    │  │
│  │  3. Select appropriate tools                        │  │
│  │  4. Execute tool calls                              │  │
│  │  5. Synthesize results                              │  │
│  │  6. Respond or ask clarifying questions             │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                       Tool Layer                            │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌─────────┐ │
│  │  search_  │  │  search_  │  │  search_  │  │  save_  │ │
│  │  flights  │  │  trains   │  │   buses   │  │itinerary│ │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └────┬────┘ │
└────────┼──────────────┼──────────────┼─────────────┼───────┘
         │              │              │             │
         ▼              ▼              ▼             ▼
┌─────────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐
│  Amadeus    │  │   SNCF   │  │  FlixBus │  │ MCP Filesys  │
│     API     │  │   API    │  │   API    │  │    Server    │
└─────────────┘  └──────────┘  └──────────┘  └──────────────┘
```

## Project Structure

```
mcp-agent-transport/
│
├── main.py                      # Entry point - interactive chat
├── test_agent.py                # Test suite
├── requirements.txt             # Python dependencies
├── mcp_config.json             # MCP server configuration
├── .env.example                # Environment template
├── .gitignore                  # Git ignore rules
│
├── agent/                       # LangGraph agent
│   ├── __init__.py
│   ├── graph.py                # ReAct agent implementation
│   ├── tools.py                # Agent tools (search, save, etc.)
│   └── prompts.py              # System prompts & formatting
│
├── apis/                        # API clients
│   ├── __init__.py
│   ├── amadeus.py              # Amadeus flight API
│   ├── trains.py               # SNCF train API
│   └── buses.py                # FlixBus API via RapidAPI
│
├── mcp/                         # Model Context Protocol
│   ├── __init__.py
│   └── client.py               # MCP filesystem client
│
├── saved_itineraries/          # Saved search results
│   └── .gitkeep
│
└── docs/                        # Documentation
    ├── README.md               # Project overview
    ├── QUICKSTART.md           # 5-minute setup guide
    ├── SETUP_GUIDE.md          # Detailed setup
    ├── API_DOCUMENTATION.md    # API details & pricing
    └── PROJECT_OVERVIEW.md     # This file
```

## Technology Choices

### Why LangGraph?
- **State Management**: Built-in conversation memory
- **Tool Calling**: Native support for function calling
- **Cyclic Flows**: ReAct pattern requires loops (agent → tools → agent)
- **Flexibility**: Easy to add new tools or modify behavior

### Why LangChain 1.0?
- **Latest Features**: New content blocks, standardized messages
- **Better Tooling**: Improved `@tool` decorator
- **Cleaner API**: Simplified abstractions
- **Future-proof**: Active development and community

### Why ReAct Pattern?
- **Reasoning**: Agent explains its thinking
- **Planning**: Can break complex tasks into steps
- **Self-correction**: Can retry with different approaches
- **Transparency**: User can see the agent's decision process

### Why These APIs?
- **Amadeus**: Most comprehensive flight API, generous free tier
- **SNCF**: Official French railway data, real-time updates
- **FlixBus**: Largest European bus network, accessible via RapidAPI

## Agent Capabilities

### What the Agent Can Do

1. **Multi-modal Search**
   - Search flights, trains, and buses simultaneously
   - Compare prices across transportation types
   - Consider both cost and travel time

2. **Intelligent Questioning**
   - Detects missing information (dates, cities, preferences)
   - Asks clarifying questions
   - Remembers context across conversation

3. **Smart Recommendations**
   - Sorts results by price or duration
   - Highlights trade-offs (e.g., "faster but more expensive")
   - Considers user preferences

4. **Data Persistence**
   - Save itineraries as JSON
   - Load previous searches
   - Track search history

5. **Real-time Data**
   - Live pricing from APIs
   - Current availability
   - Real-time schedules and delays (SNCF)

### Example Interactions

**Simple Query**
```
User: Paris to Berlin tomorrow
Agent: Could you provide the specific date in YYYY-MM-DD format?
User: 2025-11-15
Agent: Searching... [Shows flights, trains, buses]
```

**Preference-based**
```
User: I need to go from London to Amsterdam, cheapest option
Agent: When would you like to travel?
User: Next Friday
Agent: [Searches and prioritizes by price]
      The cheapest option is FlixBus at €35.90...
```

**Save & Load**
```
User: Save this as my_trip
Agent: Saved to saved_itineraries/my_trip.json
User: [Later] Load my_trip
Agent: [Displays saved itinerary]
```

## API Integration Details

### Amadeus (Flights)
- **Endpoint**: Flight Offers Search API v2
- **Free Tier**: 200-10,000 requests/month
- **Coverage**: Global airlines
- **Features**: Multi-city, one-way, round-trip

### SNCF (Trains)
- **Endpoint**: Navitia Journeys API
- **Coverage**: France + international connections
- **Features**: Real-time delays, station info
- **Note**: Pricing may require additional calls

### FlixBus (Buses)
- **Endpoint**: Via RapidAPI
- **Coverage**: 2,500+ destinations in 36 countries
- **Features**: Stations, trips, pricing, availability

## Setup Time

- **Minimal (OpenAI only)**: 2 minutes
- **With Amadeus**: +5 minutes
- **Full setup (all APIs)**: 15-20 minutes

## Cost Estimation

### Development/Testing (10-20 queries/day)
- **OpenAI GPT-4**: $0.50-1.00/day
- **Amadeus**: Free (within tier)
- **FlixBus**: Free (within tier)
- **SNCF**: Free

**Total: ~$1/day or $30/month**

### Production (100 queries/day)
- **OpenAI GPT-4**: $5-10/day
- **Amadeus**: Free + overage at €0.001-0.025/call
- **FlixBus**: May need paid tier ($10-20/month)

**Total: ~$200-300/month**

## Limitations & Future Improvements

### Current Limitations
1. **No Booking**: Agent finds options but doesn't book
2. **SNCF Coverage**: Limited to France and nearby countries
3. **Pricing Gaps**: Some train routes may not return prices
4. **No Multi-city**: Currently supports single routes only

### Potential Enhancements
1. **Additional APIs**
   - Trainline (requires partnership)
   - Eurostar, Deutsche Bahn
   - Ryanair, EasyJet direct APIs

2. **Features**
   - Multi-city routes
   - Date range searches ("cheapest day next week")
   - Price alerts
   - Booking integration

3. **UX Improvements**
   - Web interface
   - Mobile app
   - Email notifications
   - Calendar integration

4. **Advanced Agent Features**
   - Memory across sessions
   - User preferences learning
   - Proactive suggestions
   - Weather integration

## Testing

Run the test suite:
```bash
python test_agent.py
```

Tests verify:
- ✓ All dependencies installed
- ✓ API keys configured
- ✓ API clients initialize
- ✓ Tools load correctly
- ✓ Agent initializes
- ✓ Filesystem operations work

## Contributing

To extend this project:

1. **Add New Transportation API**
   - Create client in `apis/`
   - Add tool in `agent/tools.py`
   - Update documentation

2. **Enhance Agent**
   - Modify `agent/graph.py` for new behaviors
   - Add prompts in `agent/prompts.py`
   - Extend tool capabilities

3. **Add Features**
   - Multi-city routes
   - Price alerts
   - User preferences
   - Web interface

## License

MIT License - Feel free to use and modify for your projects.

## Resources

- **LangChain Docs**: https://python.langchain.com/
- **LangGraph Docs**: https://langchain-ai.github.io/langgraph/
- **Amadeus Docs**: https://developers.amadeus.com/
- **MCP Docs**: https://github.com/modelcontextprotocol/

## Support

For issues or questions:
1. Check [SETUP_GUIDE.md](SETUP_GUIDE.md)
2. Review [API_DOCUMENTATION.md](API_DOCUMENTATION.md)
3. Run test suite: `python test_agent.py`
4. Check API status pages

---

**Built with ❤️ using LangChain 1.0 and LangGraph**

This is a real, working MVP ready for production use with proper API keys configured.
