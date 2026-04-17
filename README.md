# Itinerary Generator

A multi-agent LangGraph system with two AI-powered solutions for travel planning:

- **Itinerary Generator** — transforms an attractions list into a professionally formatted day-by-day PDF itinerary with maps, images, official ticket links, and cost estimates
- **Transport Optimizer** — conversational route planner that compares transport modes, researches real costs and payment methods, and generates a PDF summary

![Python](https://img.shields.io/badge/python-3.10+-blue)
![LangChain](https://img.shields.io/badge/langchain-1.0-purple)
![LangGraph](https://img.shields.io/badge/langgraph-1.0+-green)
![License](https://img.shields.io/badge/license-MIT-orange)

---

## Architecture — Itinerary Generator

```
User Input
    │
    ▼
Coordinate Finder Agent  ← Google Places (Serper)
    │
    ▼
Day Organizer Agent      ← classify → configure → finalize → approval loop
    │
    ▼
Attraction Researcher    ← parallel (1 agent/day)
Agents
    │
    ▼
PDF Builder              ← ReportLab, route map, costs
```

## Architecture — Transport Optimizer

```
User (chat)
    │
    ▼
Route Collector Agent    ← Google Places (Serper)
    │
    ▼
Transport Researcher     ← Google Maps Directions API
Agent
    │
    ▼
Cost Calculator Agent    ← Web search (Serper)
    │
    ▼
PDF Builder
```

---

## Features — Itinerary Generator

- Intelligent classification: isolated / preference / flexible / exclusive days
- K-means geographic clustering with optional min/max per day
- Route optimization: nearest-neighbor within each day, configurable start/end points
- Interactive approval flow (CLI interrupt)
- Parallel attraction research (one agent per day)
- Image search with 30+ watermark domains filtered + URL validation
- Official ticket links only (11+ reseller domains blocked)
- Duplicate attraction detection (multi-day occurrences)
- Compound attractions (sub-locations researched separately)
- Free-only preference detection
- Multi-language output (pt-br, en, es, fr)
- PDF with table of contents, route map, images, clickable links, cost summary
- Optional email delivery (SMTP/Gmail)

## Features — Transport Optimizer

- Conversational route definition via natural chat
- Multi-mode comparison: walking, transit, driving (Google Maps Directions API)
- Smart preference rules (e.g., "always walk if under 20 min")
- Real pricing research with source links
- Payment method analysis with pros/cons
- Conversation summarization for long sessions (80k token threshold)
- PDF: route table, costs, price explanations, payment methods

---

## Quick Start

```bash
# 1. Clone and install dependencies
git clone <repository-url>
cd itinerary-generator
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys (see Configuration below)

# 3. Run the CLI
python main.py
```

---

## Configuration

Create a `.env` file with the following:

```bash
# OpenRouter API (required) - https://openrouter.ai/keys
OPENROUTER_API_KEY=sk-or-...

# Model Configuration — per-agent or global fallback
# Browse models at: https://openrouter.ai/models
COORDINATE_FINDER_MODEL=anthropic/claude-sonnet-4-20250514
DAY_ORGANIZER_MODEL=anthropic/claude-sonnet-4-20250514
ATTRACTION_RESEARCHER_MODEL=anthropic/claude-sonnet-4-20250514
MODEL_NAME=anthropic/claude-sonnet-4-20250514

# Serper API (required — Google Places + Google Search) - https://serper.dev
SERPER_API_KEY=...

# Tavily API (required — web search + image retrieval) - https://tavily.com
TAVILY_API_KEY=tvly-...

# Google Maps API (required for Transport Optimizer)
GOOGLE_MAPS_API_KEY=...

# Email delivery (optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password

# Observability (optional)
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=lsv2_pt_...
LANGSMITH_PROJECT=itinerary-generator
```

---

## Day Organizer — 3-Step Workflow

The Day Organizer runs a structured 3-step process before requesting user approval:

1. **classify_attractions** (required) — classifies every attraction as isolated, preference, flexible, or exclusive, and assigns fixed days where applicable
2. **configure_route_optimization** (optional) — sets starting and ending points per day for route ordering
3. **configure_day_constraints** (optional) — sets minimum and maximum attraction counts per day for K-means clustering
4. **finalize_day_organization** (required) — executes K-means clustering on flexible attractions and applies nearest-neighbor ordering within each day
5. **request_itinerary_approval** — presents the result and waits for user approval or revision

---

## User Preference Types

| Type | Example | Behavior |
|------|---------|----------|
| **Isolated** | "Disneyland needs a full day" | Exclusive day, no other attractions added |
| **Preference** | "Eiffel Tower on day 1" | Fixed day, can share with others |
| **Exclusive** | "Day 3 is only for X and Y" | Fixed set, closed to flexible additions |
| **Flexible** | Just listing attractions | K-means geographic grouping |

---

## Project Structure

```
itinerary-generator/
├── main.py
├── requirements.txt
├── .env.example
├── src/
│   ├── itinerary_generator/
│   │   ├── graph.py
│   │   ├── state.py
│   │   ├── agent_definition.py
│   │   ├── tools.py
│   │   ├── prompts.py
│   │   └── other_nodes.py
│   ├── transport_optimizer/
│   │   ├── graph.py
│   │   ├── state.py
│   │   ├── agent_definition.py
│   │   ├── tools.py
│   │   └── prompts.py
│   ├── processor/
│   │   └── pdf_processor.py      # ReportLab PDF generation
│   ├── middleware/
│   │   ├── structured_output_validator.py
│   │   ├── summarization_middleware.py
│   │   └── handoff_tool_validator.py
│   ├── mcp_client/
│   │   └── tavily_client.py
│   └── utils/
└── .results/
```

---

## Tools Reference

### Itinerary Generator

| Agent | Tool | Purpose |
|-------|------|---------|
| Coordinate Finder | `search_place_address` | Google Places search + store coordinates |
| Coordinate Finder | `return_invalid_input_error` | Handle invalid input |
| Day Organizer | `classify_attractions` | Classify all attractions (step 1) |
| Day Organizer | `configure_route_optimization` | Set start/end points per day (optional) |
| Day Organizer | `configure_day_constraints` | Set min/max per day (optional) |
| Day Organizer | `finalize_day_organization` | Execute K-means + nearest-neighbor ordering (step 3) |
| Day Organizer | `request_itinerary_approval` | Pause for user review |
| Day Organizer | `update_itinerary_organization` | Apply user changes |
| Attraction Researcher | `search_attraction_info` | Web search for details, hours, costs |
| Attraction Researcher | `search_attraction_images` | Image search with watermark filtering (Tavily) |
| Attraction Researcher | `search_ticket_link` | Official ticket URLs only |

### Transport Optimizer

| Agent | Tool | Purpose |
|-------|------|---------|
| Route Collector | `search_place_coordinates` | Find and validate place coordinates |
| Route Collector | `register_route_pair` | Store origin→destination pair |
| Route Collector | `confirm_route_pairs` | Finalize route list and hand off |
| Transport Researcher | `get_transport_options` | Google Maps Directions API |
| Transport Researcher | `register_user_preference` | Store mode selection per route |
| Transport Researcher | `finish_transport_research` | Hand off to cost calculator |
| Cost Calculator | `search_transport_information` | Research pricing via web search |
| Cost Calculator | `route_reasoning` | Analyze simple vs compound routes |
| Cost Calculator | `register_route_cost` | Store cost per route with explanation |
| Cost Calculator | `register_payment_methods` | Store payment options with pros/cons |
| Cost Calculator | `finish_interaction` | Trigger PDF generation |

---

## API Requirements

| Service | Purpose | Notes |
|---------|---------|-------|
| OpenRouter | LLM access (Claude, GPT-4, Gemini, etc.) | Pay per token |
| Serper | Google Places + Google Search | 2,500 searches to start |
| Tavily | Web search + image retrieval | 1,000 searches/month |
| Google Maps | Directions API (Transport Optimizer) | Pay per request |

---

## Tech Stack

- **LangChain 1.0 / LangGraph** — agent orchestration and workflow management
- **OpenRouter** — multi-provider LLM access (Claude, GPT-4, Gemini, etc.)
- **Serper** — Google Places and Google Search
- **Tavily** — web search and image retrieval
- **Google Maps Directions API** — transport mode comparison
- **scikit-learn / k-means-constrained** — geographic clustering with optional size constraints
- **ReportLab** — PDF generation
- **GeoPandas / Matplotlib** — route map visualization

---

## License

MIT License — free to use and modify
