# Itinerary Generator

A multi-agent LangGraph system that transforms a list of tourist attractions into comprehensive day-by-day travel itineraries with geographic optimization, detailed research, and professional DOCX document generation.

![Python](https://img.shields.io/badge/python-3.10+-blue)
![LangChain](https://img.shields.io/badge/langchain-1.0-purple)
![LangGraph](https://img.shields.io/badge/langgraph-1.0+-green)
![License](https://img.shields.io/badge/license-MIT-orange)

## Features

### Day Organization
- **Intelligent Clustering**: K-means groups attractions by geographic proximity
- **Constrained Clustering**: Set min/max attractions per day while keeping the number of days fixed
- **User Approval Flow**: Review and adjust K-means organized itineraries before proceeding
- **User Preference Handling**: Supports isolated days, specific day assignments, or flexible grouping

### Research & Content
- **Parallel Research**: Multiple agent instances research attractions concurrently
- **Rich Descriptions**: 150-300 word detailed descriptions with history, curiosities, and insider tips
- **Official Ticket Links**: Only links from official websites (never TripAdvisor, Viator, etc.)
- **Compound Attraction Support**: Multi-location entries with per-attraction pricing

### Image Quality
- **Watermark Filtering**: Automatically excludes images from 35+ stock photo domains (Shutterstock, Getty, Alamy, etc.)
- **Resolution Filtering**: Discards low-resolution images (minimum 250,000 pixels area)
- **Curated Selection**: Searches 3x more images than needed to ensure quality after filtering

### Document Generation
- **Professional DOCX Output**: Styled documents with visual route maps
- **Clean Titles**: Agent generates polished attraction titles (not raw user input)
- **Multi-Language Support**: English, Portuguese (BR), Spanish, French with strict consistency
- **Cost Summary**: Grouped by currency with per-person estimates

### Other
- **Per-Agent Model Configuration**: Use different LLM models for each agent (e.g., Claude for organizing, GPT-4 for research)
- **Address-Based Geocoding**: Google Places search for accurate coordinates
- **Multilingual Maps**: Preserves clean attraction titles on route maps
- **Email Delivery**: Send generated itineraries via SMTP

## Architecture

The system uses LangGraph to orchestrate specialized agents in a pipeline:

```
User Input (attractions list)
         │
         ▼
┌─────────────────────────────┐
│  Day Organizer Agent        │
│  1. Search official address │  ← Uses web search for accurate geocoding
│  2. Build name→address map  │  ← Preserves user's language in keys
│  3. Extract coordinates     │
│  4. K-means clustering      │  ← Supports min/max constraints
│  5. Request user approval   │  ← Interactive review for flexible attractions
│  6. Respect user prefs      │
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  Attraction Researcher      │  Parallel instances (one per day)
│  Agents                     │  research details, images, costs
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│  Document Builder           │  - Filters watermarked images
│                             │  - Filters low-resolution images
│                             │  - Generates DOCX with maps
│                             │  - Maps use clean titles
└─────────────────────────────┘
         │
         ▼
    DOCX Output + Optional Email
```

## Tech Stack

- **LangChain 1.0** / **LangGraph** - Agent orchestration with TypedDict state schemas
- **OpenRouter** - Access to multiple LLM providers (Claude, GPT-4, Gemini, Grok, Llama, etc.)
- **Serper** - Google Places for address search
- **Tavily** - Web search and image retrieval
- **GeoPy** - Geocoding via Nominatim
- **scikit-learn** / **k-means-constrained** - K-means clustering with size constraints
- **GeoPandas** / **Matplotlib** - Route map visualization
- **python-docx** - Document generation

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

## Configuration

Create a `.env` file with the following:

```bash
# OpenRouter API (required) - https://openrouter.ai/keys
OPENROUTER_API_KEY=sk-or-...

# Model Configuration - Per-Agent or Global
# Browse models at: https://openrouter.ai/models

# First agent - organizes attractions into days
DAY_ORGANIZER_MODEL=anthropic/claude-sonnet-4-20250514

# Second agent - researches attraction details
ATTRACTION_RESEARCHER_MODEL=anthropic/claude-sonnet-4-20250514

# Fallback model (used if specific agent model not set)
MODEL_NAME=anthropic/claude-sonnet-4-20250514

# Other model examples: openai/gpt-4o, google/gemini-pro-1.5, x-ai/grok-3

# Serper API (required for place address search) - https://serper.dev
SERPER_API_KEY=...

# Tavily API (required for web search and images) - https://tavily.com
TAVILY_API_KEY=tvly-...

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

## Usage

The CLI guides you through the itinerary creation process:

1. **Enter attractions** (one per line, end with "END"):
   ```
   Torre Eiffel
   Museu do Louvre
   Catedral de Notre-Dame
   Palácio de Versalhes
   END
   ```

2. **Add preferences** (optional):
   ```
   Versalhes precisa de um dia inteiro
   No máximo 3 atrações por dia
   ```

3. **Select options**:
   - Number of days
   - Output language (en, pt-br, es, fr)

4. **Review organization** (for flexible attractions):
   ```
   ============================================================
   PROPOSED ITINERARY ORGANIZATION
   ============================================================

   Day 1:
     • Torre Eiffel
     • Catedral de Notre-Dame

   Day 2:
     • Museu do Louvre

   Day 3:
     • Palácio de Versalhes

   ============================================================

   Is this organization okay?
   Type 'yes' to approve, or describe what changes you'd like.
   Examples: 'move Louvre to day 2', 'swap day 1 and day 3'

   Your response:
   ```

5. **Receive output**:
   - Generated DOCX saved to `.results/`
   - Cost summary by currency displayed
   - Option to send via email

## User Preference Types

The Day Organizer understands three types of user intent:

| Type | Example | Behavior |
|------|---------|----------|
| **Isolated** | "Disneyland needs a full day" | Attraction gets exclusive day |
| **Specific Day** | "Eiffel Tower on day 1" | Assigned to day, can share with others |
| **Flexible** | Just listing attractions | Grouped by geographic proximity |

### Free-Only Attractions

When you indicate you won't pay for an attraction, the researcher agent respects this:

| Input | Behavior |
|-------|----------|
| "Torre Eiffel (arredores, não vou entrar)" | No ticket prices, focuses on free experience |
| "Colosseum (outside only)" | Description covers exterior views and photo spots |
| "Louvre (free part only)" | No paid entry info, only free areas covered |

### Clustering Constraints

You can specify min/max attractions per day:

| Constraint | Example | Behavior |
|------------|---------|----------|
| **Minimum** | "at least 2 per day" | Each day has >= 2 attractions |
| **Maximum** | "no more than 3 per day" | Each day has <= 3 attractions |
| **Both** | "between 2 and 4 per day" | Days have 2-4 attractions |

The number of days remains fixed; only cluster sizes are constrained using `k-means-constrained`.

## Multilingual Support

The system preserves attraction names in your language:

1. **Input**: You provide names in your language (e.g., "Torre Eiffel", "Museu do Louvre")
2. **Geocoding**: Agent finds English addresses for accurate coordinates
3. **Storage**: Your original names are used as keys
4. **Output**: Maps and documents display clean titles in your language

### Strict Language Consistency

The researcher agent enforces strict language rules:
- ALL content (descriptions, captions, ticket info) must be in the selected language
- No mixing languages (e.g., "A view incrível" is invalid)
- Proper nouns (attraction names, street names) stay in original form
- Even when researching from English sources, content is translated

Example mapping:
```python
{
    "Torre Eiffel": "Eiffel Tower, Champ de Mars, Paris, France",
    "Museu do Louvre": "Louvre Museum, Rue de Rivoli, Paris, France"
}
```

## Image Quality Filtering

The system applies two layers of image filtering to ensure high-quality documents:

### 1. Watermark Domain Filtering
Images from 35+ stock photo sites are automatically excluded:
- Shutterstock, Getty Images, iStock
- Alamy (including CDN subdomains like c7.alamy.com, c8.alamy.com)
- Adobe Stock, Dreamstime, 123RF, Depositphotos
- And many more...

### 2. Resolution Filtering
Low-resolution images are discarded during document generation:
- Minimum area: 250,000 pixels (equivalent to 500×500)
- Allows various aspect ratios (panoramic, portrait, square)
- Filtering happens after download, no extra API calls

To compensate for filtered images, the system searches 3x more images than needed.

## Project Structure

```
itinerary-generator/
├── main.py                              # CLI entry point
├── requirements.txt                     # Dependencies
├── .env.example                         # Configuration template
│
├── src/
│   ├── agent/
│   │   ├── graph.py                    # LangGraph workflow definition
│   │   ├── state.py                    # TypedDict state schemas
│   │   ├── agent_definition.py         # Agent creation and node functions
│   │   ├── tools.py                    # Search, geocoding, clustering, approval tools
│   │   ├── prompts.py                  # System prompts for agents
│   │   └── other_nodes.py              # Helper nodes (assign_workers, build_document)
│   │
│   ├── processor/
│   │   ├── docx_processor.py           # DOCX document generation
│   │   └── email_processor.py          # SMTP email client
│   │
│   ├── mcp_client/
│   │   └── tavily_client.py            # Tavily MCP for web/image search
│   │
│   ├── middleware/
│   │   └── structured_output_validator.py  # Output validation with retry
│   │
│   └── utils/
│       ├── logger.py                   # Rich CLI logging
│       ├── observability.py            # LangSmith integration
│       └── utilities.py                # Geospatial plotting helpers
│
└── .results/                            # Generated DOCX files
```

## Available Tools

### Day Organizer Agent

| Tool | Purpose |
|------|---------|
| `search_place_address` | Google Places search + auto-store coordinates (Serper) |
| `organize_attractions_by_days` | K-means clustering with constraints |
| `request_itinerary_approval` | Pause for user review (uses LangGraph interrupt) |
| `update_itinerary_organization` | Apply user's requested changes |
| `return_invalid_input_error` | Handle invalid/unrelated input |

### Attraction Researcher Agent

| Tool | Purpose |
|------|---------|
| `search_attraction_info` | Web search for details, hours, tickets (Tavily) |
| `search_attraction_images` | Image search with watermark filtering (Tavily) |

## Output Example

The generated DOCX includes:

- **Cover page** with itinerary title
- **Day-by-day sections** with:
  - Clean, polished attraction titles (e.g., "Eiffel Tower & Trocadero" instead of "eiffel tower and surroundings (enter, trocadero)")
  - Rich descriptions (150-300 words) with history, curiosities, and insider tips
  - Opening hours and addresses
  - High-quality images only (watermarked and low-resolution images filtered out)
  - Image captions describing what each photo shows
  - Ticket info with per-attraction pricing for compound attractions
  - Official ticket purchase links (never third-party booking sites)
  - Estimated costs per person
- **Visual route map** with color-coded day markers using clean titles
- **Cost summary** grouped by currency

## API Requirements

| Service | Purpose | Free Tier |
|---------|---------|-----------|
| OpenRouter | LLM access (Claude, GPT-4, Gemini, etc.) | Pay per token |
| Serper | Google Places (address search) | 2,500 searches to start |
| Tavily | Web search + images | 1,000 searches/month |

## Geocoding Accuracy

The agent uses Google Places (via Serper) to get accurate coordinates directly:

1. **Search**: `search_place_address(original_name="Coliseu", query="Colosseum Rome Italy")`
2. **Auto-Store**: Coordinates from Google Places are stored automatically in state
3. **Preserve Language**: User's original name is used as the key

This approach:
- Gets coordinates directly from Google Places (no separate geocoding step)
- Prevents errors with attractions that have namesakes in other cities
- Preserves your language in map labels and outputs

## Troubleshooting

**Geocoding failures**: The agent will search for official addresses before geocoding. If issues persist, ensure attraction names include city and country.

**Rate limits**: The system includes exponential backoff retry. For high volume, consider adding delays between requests.

**Approval not requested**: The middleware validates that `request_itinerary_approval` is called when K-means clustering is used. If skipped, the agent will retry.

## License

MIT License - Free to use and modify
