# Transport Route Optimizer

**AI-powered transport route optimizer that compares transport options, researches real costs, and generates a professional PDF summary.**

---

## The Problem

Navigating public transport in an unfamiliar city is overwhelming. Different metro lines, bus systems, transit cards, and fare rules make planning a basic route confusing — even before factoring in transfers and time constraints.

Travelers don't know when it's better to walk, take the subway, or grab a taxi — and what each option actually costs. A 15-minute metro ride might cost less than expected, or a taxi might be unavoidably necessary for certain routes.

Pricing information is scattered across transit authority websites, often in the local language and hard to find. Reseller sites and aggregators add noise without providing reliable fare data.

There is no single tool that compares all transport modes for your specific routes, researches real costs, explains payment options, and gives you a clear summary to reference during your trip.

---

## What It Does

The user defines city routes (A→B, B→C, etc.) through natural conversation. The system delivers transport options comparison (walking, transit, driving), real pricing, payment methods, and a PDF summary.

---

## How It Works

### Step 1 — Route Collection

A conversational agent collects route pairs through natural dialogue — no forms or structured input required. The user describes their routes however feels natural, and the agent identifies and validates each location via the Google Places API (caching a routable `place_id` for each place). When all routes are defined, the user confirms and the system moves on.

### Step 2 — Transport Overview (silent)

Before comparing routes, a silent agent researches, once, how public transport pricing and ticketing work in the city in general: single-ticket prices, whether a ticket is shared across modes on one trip or each leg is paid separately, transfer rules, day/week passes, and airport fares (which usually differ). This general summary is saved and handed to the later agents so route pricing is grounded in the city's real fare model. This step runs automatically with no user interaction.

### Step 3 — Transport Research

The system queries the Google Maps Directions API for each route and presents walking, transit, and driving options with duration, distance, transit details (line name, number of stops, transfers), and an **estimated price per option** taken verbatim from the overview (never invented; the exact cost is confirmed later). The user selects their preferred mode per route. When a user sets a rule (e.g., "always walk if under 20 minutes"), it is applied automatically to all compatible routes without asking again.

### Step 4 — Cost Calculation

The system researches real transport pricing via web search for each paid route, applying the overview's fare-integration and transfer rules for multi-leg routes and combined tickets. After costs are resolved, it asks the user about preferred payment methods and researches those with pros and cons, and researches transport-tracking apps relevant to the user's context.

### Step 5 — PDF Generation

A professional document is generated with an estimate disclaimer, a route overview table, cost breakdown, price explanations with source links, a payment method comparison, and a transport-tracking apps section.

---

## Detailed Capabilities

### Conversational Interface

Routes are defined via natural chat — no forms or structured input required. The agent asks clarifying questions when needed (e.g., distinguishing sequential from independent routes) and confirms the full list before proceeding.

### Multi-Mode Comparison

Walking, subway, bus, train, and driving options are retrieved via the Google Maps Directions API, with full details: vehicle type, line name, number of stops, and transfer points. Up to three alternatives are kept per **resolved** mode (3 train, 3 bus, 3 subway, …) rather than three total transit results — otherwise trains get hidden behind the subway/bus alternatives Google returns first. Routing uses each place's cached `place_id` so large venues (airports, big parks, stations) snap to a walkable access point instead of an internal pin that would otherwise inflate a transit result with a huge phantom walking leg.

### Representative Departure Time

Transit availability and duration depend on the departure time. Querying at the current instant can fall outside service hours — for example airport trains, which do not run overnight — so those services wouldn't appear. When it's already daytime at the origin the tool uses the real-time "now"; when it's late night it shifts to a representative daytime hour so scheduled daytime services show up. The local time is derived offline from longitude (no timezone API call).

### Smart Preference Rules

When the user expresses a rule (e.g., "always walk if under 20 minutes"), the system applies it automatically across all qualifying routes without asking again. Questions and automatic registrations are kept separate — the agent never asks and executes in the same response.

### Coordinate Caching

Locations already validated are reused from cache, avoiding redundant Google Places API calls across routes that share common endpoints.

### Pricing Research

Real transport costs are retrieved via web search with current date context, ensuring up-to-date pricing. Source links are included in every cost entry for full transparency.

### Transfer Rules

For multi-leg routes, the system researches transfer discounts, combined tickets, and time windows. A route combining metro and bus, for example, is analyzed to determine whether a single ticket covers the full journey.

### Payment Methods

After all costs are resolved, the system asks the user about payment preferences (transit card, contactless, cash, app) and researches each method with pros, cons, and source links.

### Transport-Tracking Apps

The system researches apps the traveler can use to plan and track transport (journey planners, live-tracking apps) relevant to the user's context and city, and includes them in the PDF with a short description, supported platforms, and links.

### Conversation Summarization

Long conversations are automatically summarized when they exceed 80,000 tokens. The summary preserves all critical information: city, route pairs, transport options, user preferences, costs, and current progress. The 10 most recent messages are kept as immediate context alongside the summary.

### Multi-Language Support

Full support for Portuguese (BR), English, Spanish, and French. PDF labels and transport mode names are translated per language.

### PDF Summary

The generated PDF includes an estimate disclaimer (routes and prices are estimates that may vary with schedules and the time the search was run), a route overview table (from → to → mode → duration → cost), a cost breakdown with grand total, per-route price explanations with source links, a payment method section, and a transport-tracking apps section — all localized.

---

## Quality Guarantees

- Handoff validation ensures each agent completes its required steps before transitioning to the next
- Structured output enforcement with automatic retry on validation failure
- Conversation summarization preserves all route pairs, preferences, and costs across long interactions
- Workflow integrity middleware prevents incomplete agent transitions
- All transport data retrieved from Google Maps API — agents are prohibited from estimating or inventing route information
- Prices shown during selection must come verbatim from the researched overview — inventing a fare is forbidden; when the overview lacks a figure the option is marked "to be confirmed"
- Completeness check verifies all routes have preferences registered, costs calculated, and transport apps registered before PDF generation

---

## Delivery

The system runs as an interactive CLI chat application. The user converses naturally with the system through the terminal, reviewing transport options at each step and receiving the final PDF at the end.

---

## Architecture Overview

The pipeline consists of four specialized AI agents orchestrated by LangGraph:

1. **Route Collector** — conversational agent that collects and validates route pairs via Google Places
2. **Transport Overview** — silent agent that researches the city's general fare/ticketing model once and hands the summary to the later agents
3. **Transport Researcher** — queries Google Maps Directions API, presents options with overview-grounded estimated prices, and records user preferences
4. **Cost Calculator** — researches real pricing via web search, handles transfer rules, and researches payment methods and transport-tracking apps

The graph supports conditional entry points, allowing execution to resume at any agent based on saved state. A summarization middleware handles long conversations, and a handoff validation middleware enforces workflow integrity between agents.
