# Itinerary Generator

**AI-powered itinerary generator that creates professional day-by-day travel documents with maps, images, official ticket links, and cost estimates.**

---

## The Problem

Planning a multi-day trip is time-consuming and error-prone. Travelers spend hours searching for attraction information, ticket links, opening hours, and images across dozens of websites — and then still have to organize everything manually.

Organizing attractions by day requires geographic awareness. Grouping nearby places together avoids wasting time commuting across the city, but manually doing this for ten or twenty attractions is impractical.

Finding reliable, official ticket links is frustrating. Search results are dominated by resellers and booking platforms that charge markups or redirect to third-party checkout flows.

There is no single tool that takes a list of attractions and produces a ready-to-use, professional travel document with maps, images, costs, and links.

---

## What It Does

The user provides a list of attractions, the number of travel days, and optional preferences (age group, interests, fixed-day assignments). The system delivers a professional PDF with day-by-day organization, attraction descriptions, images, ticket links, a route map per day, and a cost breakdown.

---

## How It Works

### Step 1 — Coordinate Discovery

The system finds GPS coordinates for every attraction via the Google Places API. If a search fails, it retries with alternative queries. It also detects when the same attraction appears across multiple days and handles duplicates consistently.

### Step 2 — Smart Day Organization

Attractions are classified into three categories:

- **Isolated** — full-day attractions (e.g., Disneyland, day trips) that receive an exclusive day with no other additions
- **Preference** — attractions with a user-assigned day that can still share that day with others
- **Flexible** — attractions with no day assignment, grouped by geographic proximity using K-means clustering

Users can also define **Exclusive Days**: days that contain a fixed, complete set of attractions and are closed to any flexible additions.

### Step 3 — User Approval

After the day organization is proposed, the user can approve it, request specific moves (e.g., "move the museum to day 2"), or reclassify attractions. This is an iterative loop that continues until the user is satisfied.

### Step 4 — Parallel Attraction Research

One AI agent per day runs simultaneously. Each agent researches descriptions, images, official ticket links, and costs for every attraction on that day. Running in parallel means a 7-day itinerary takes the same time as a 1-day itinerary.

### Step 5 — PDF Generation

The system assembles a professional document with a table of contents, a visual route map per day, day-by-day sections with images and clickable links, and a cost summary.

---

## Detailed Capabilities

### Multi-Language Support

Input is accepted in any language. Output documents are produced in Portuguese (BR), English, Spanish, or French, with strict language consistency enforced throughout.

### Intelligent Classification System

| Type | Example | Behavior |
|------|---------|----------|
| Isolated | "Disneyland needs a full day" | Exclusive day, no other attractions added |
| Preference | "Eiffel Tower on day 1" | Fixed day, can share with others |
| Exclusive | "Day 3 is only for X and Y" | Fixed day, closed to flexible additions |
| Flexible | Just listing attractions | System optimizes placement by geography |

### Geographic Clustering

Flexible attractions are grouped using K-means clustering. Optional minimum and maximum constraints per day can be configured (e.g., "at most 3 attractions per day"). The number of days remains fixed; only cluster sizes are constrained.

### Route Optimization

Within each day, attractions are ordered using a nearest-neighbor algorithm to minimize travel. Users can configure a starting point and ending point per day.

### Itinerary Approval Flow

After day organization is proposed, the system pauses and waits for user input. The user can approve, request moves, or reclassify attractions. The loop runs until the user explicitly approves.

### Parallel Research

One dedicated AI agent runs per day, all simultaneously. Research for day 1 and research for day 7 happen at the same time, keeping total processing time constant regardless of trip length.

### Image Search and Validation

Images are retrieved via Tavily. Over 30 watermark and stock photo domains are filtered (Shutterstock, Getty, Alamy, Adobe Stock, etc.). Every image URL is verified as accessible before being included in the PDF.

### Official Ticket Links

Ticket links are found via targeted Google search filtered to official sites only. Over 11 reseller domains are blocked (Viator, TripAdvisor, GetYourGuide, Klook, etc.). All URLs are validated before inclusion.

### Duplicate Attraction Handling

When the same attraction appears on multiple days, each instance gets a day-suffixed label (e.g., "Bondi Beach (day 1)", "Bondi Beach (day 3)") to keep research outputs distinct.

### Compound Attractions

Some entries contain multiple sub-locations (e.g., "Vatican Museums + Sistine Chapel + St. Peter's Basilica"). Each sub-location is researched separately and compiled into a single attraction entry with individual pricing.

### Free-Only Preference Detection

When a user indicates they will not enter a paid attraction (e.g., "Colosseum — exterior only"), the system detects this, sets cost to zero, and focuses the description on the free experience (exterior views, surroundings, photo spots).

### Combined Ticket Logic

When multiple attractions share a combined ticket, the first attraction carries the full cost and subsequent ones are marked as zero with a note explaining the combined entry.

### Cost Breakdown

Costs are presented per person, grouped by currency (EUR, USD, BRL, etc.), with a summary card showing totals per currency.

### Route Map

Each day includes a visual map with numbered markers and connecting lines showing the order of visits.

### PDF Output

The generated PDF includes a table of contents, day-by-day sections with descriptions, images, opening hours, ticket links, and useful links, plus a final cost summary.

### Email Delivery

The completed PDF can optionally be delivered via email using SMTP or Gmail.

---

## Quality Guarantees

- All image URLs verified accessible before inclusion
- All ticket links verified as official and working
- Every attraction validated to be researched — coverage check prevents omissions
- Structured output schema enforcement with up to 3 automatic retries per agent
- Workflow integrity validation — agents must complete all required steps before proceeding

---

## Delivery

The system runs as an interactive CLI application. The user is guided through each step in the terminal: entering attractions, providing preferences, reviewing the proposed organization, and receiving the final PDF.

---

## Architecture Overview

The pipeline consists of three specialized AI agents orchestrated by LangGraph:

1. **Coordinate Finder** — resolves GPS coordinates for every attraction
2. **Day Organizer** — classifies, clusters, and proposes day organization; iterates with user until approved
3. **Attraction Researcher** — one agent per day, all running in parallel, researching descriptions, images, links, and costs

A middleware layer handles output validation, retry logic, and workflow integrity checks between agents.
