"""State schema and TypedDict models for the transport optimizer agent group."""
from typing import TypedDict, Annotated, List, Dict, Optional, Any
from langchain.agents import AgentState
from langchain_core.messages import BaseMessage
import operator

def operator_add_without_duplicates(list1: List[Any], list2: List[Any]) -> List[Any]:
    """Custom operator.add that appends items from list2 to list1 without duplicates."""
    existing_items = list(tuple(sorted(item.items())) if isinstance(item, dict) else item for item in list1)
    for item in list2:
        identifier = tuple(sorted(item.items())) if isinstance(item, dict) else item
        if identifier not in existing_items:
            list1.append(item)
            existing_items.append(identifier)
    return list1


def last_value(existing: list, new: list) -> list:
    """Reducer that replaces the list entirely with the new value (last writer wins)."""
    return new

def keep_bigger_value(existing: int, new: int) -> int:
    """Reducer that keeps the bigger integer value."""
    return max(existing, new)


def upsert_by_pair_index(existing: list, new: list) -> list:
    """Reducer that keeps only the latest cost analysis per pair_index."""
    result = {item["pair_index"]: item for item in existing}
    for item in new:
        result[item["pair_index"]] = item
    return sorted(result.values(), key=lambda x: x["pair_index"])


# ============================================================================
# TypedDict Models for Route Data
# ============================================================================

class PlaceCoordinates(TypedDict):
    """Cached place lookup: coordinates plus a routable Google place_id."""
    lat: float
    lon: float
    place_id: Optional[str]    # Google place_id for directions (None if unresolved)
    address: str               # Formatted address from Serper Places
    title: str                 # Place display title from Serper Places


class RoutePair(TypedDict):
    """A single route segment from A to B."""
    pair_index: int            # Index of this pair (for ordering)
    start_place: str           # Search key (for API lookups)
    end_place: str             # Search key (for API lookups)
    start_display: str         # User-friendly display name
    end_display: str           # User-friendly display name
    start_coords: Optional[Dict[str, float]]  # {lat: float, lon: float}
    end_coords: Optional[Dict[str, float]]    # {lat: float, lon: float}


class TransportOption(TypedDict):
    """Transport option for a route pair."""
    mode: str                  # "walking", "subway", "bus", "train", "taxi", "driving"
    duration_minutes: int      # Total travel time in minutes
    distance_km: float         # Distance in kilometers
    currency: str              # Currency code (EUR, USD, GBP, etc.)
    details: str               # Line numbers, transfer info, walking directions, etc.
    steps: List[str]           # Step-by-step instructions


class UserPreference(TypedDict):
    """User's selected transport for a route pair."""
    pair_index: int            # Index of the route pair
    selected_mode: str         # The mode user selected
    transport_details: TransportOption  # Full details of selected option


class PaymentMethod(TypedDict):
    """Payment method for transport."""
    name: str                  # "Metro Card", "Apple Pay", "Paper Ticket", etc.
    description: str           # How to use this payment method
    setup_required: bool       # Whether user needs to acquire something beforehand
    refillable: bool           # Whether it's a reusable/refillable option


class TransportCostInfo(TypedDict):
    """Cost information for a transport mode."""
    mode: str                  # Transport mode (subway, bus, etc.)
    single_trip_cost: float    # Cost per single trip
    day_pass_cost: Optional[float]      # Cost for day pass (None if not available)
    weekly_pass_cost: Optional[float]   # Cost for weekly pass (None if not available)
    currency: str              # Currency code
    payment_methods: List[PaymentMethod]  # Available payment methods
    observation: Optional[str]  # Discounts, special rules, notes


class RouteCostAnalysis(TypedDict):
    """Cost analysis for a specific route pair."""
    pair_index: int                    # Which route pair (0-based)
    is_compound: bool                  # True if multiple legs/modes
    modes: List[str]                   # Transport modes involved
    total_cost: float                  # Total cost for this route
    currency: str                      # Currency code
    explanation: str                   # Detailed explanation of pricing
    rules_applied: Optional[str]       # Transfer rules, discounts applied
    source_links: List[str]            # URLs where pricing was found


class PaymentMethodInfo(TypedDict):
    """Detailed payment method information."""
    name: str                          # Payment method name
    description: str                   # Step-by-step how to use
    pros: List[str]                    # Advantages
    cons: List[str]                    # Disadvantages
    source_links: List[str]            # Source URLs


class TransportOverview(TypedDict):
    """General overview of how transport costs/ticketing work in the city.

    Researched once (transport_overview agent) before route research. All the
    specifics (prices, fare integration, transfer rules, passes) live in the
    free-text summary — kept intentionally minimal.
    """
    summary: str                       # Free-text general overview
    source_links: List[str]            # Source URLs


class TransportApp(TypedDict):
    """A transport-tracking app the traveler can use (e.g. journey planners)."""
    name: str                          # App name
    description: str                   # What it does / how it helps
    platforms: List[str]               # e.g. ["iOS", "Android", "Web"]
    source_links: List[str]            # Official/store URLs


# ============================================================================
# Graph State
# ============================================================================

class TransportOptimizerState(AgentState):
    """Main state for the transport optimizer multi-agent system."""

    summary_message: BaseMessage

    # -------------------------------------------------------------------------
    # Agent Routing
    # -------------------------------------------------------------------------
    # Each agent sets this when handing off to the next agent
    # Possible values: "route_collector", "transport_researcher", "cost_calculator", "end"
    next_agent: str

    # -------------------------------------------------------------------------
    # Route Collector Outputs
    # -------------------------------------------------------------------------
    # The city/area being navigated (e.g., "Paris", "Rome")
    city: str

    # Starting point of the journey
    starting_point: str

    # List of route pairs collected from user
    # Uses operator_add_without_duplicates to accumulate pairs registered via register_route_pair tool
    route_pairs: Annotated[List[RoutePair], operator_add_without_duplicates]

    # Whether user has confirmed all pairs are complete
    pairs_confirmed: bool

    # -------------------------------------------------------------------------
    # Transport Overview (general city ticketing/cost research, runs once)
    # -------------------------------------------------------------------------
    # General overview of how transport costs work in the city (summary + links)
    transport_overview: TransportOverview

    # Whether the general overview research is complete
    transport_overview_complete: bool

    # -------------------------------------------------------------------------
    # Coordinates Cache (shared between agents)
    # -------------------------------------------------------------------------
    # Coordinates by place name (populated by search_place_coordinates)
    # Key: normalized place name, Value: PlaceCoordinates (lat, lon, place_id, address, title)
    place_coordinates: Annotated[Dict[str, PlaceCoordinates], operator.or_]

    # -------------------------------------------------------------------------
    # Transport Researcher Outputs
    # -------------------------------------------------------------------------
    # Transport options for each pair (pair_index -> list of options)
    # Uses operator.or_ to merge updates from different calls
    transport_options: Annotated[Dict[int, List[TransportOption]], operator.or_]

    # User's selected preferences (accumulated list)
    user_preferences: Annotated[List[UserPreference], operator_add_without_duplicates]

    # Current pair being processed (0-indexed)
    current_pair_index: Annotated[int, keep_bigger_value]

    # Whether all preferences have been collected
    all_preferences_collected: bool

    # -------------------------------------------------------------------------
    # Cost Calculator Outputs
    # -------------------------------------------------------------------------
    # Cost analysis per route (accumulated via operator.add)
    route_cost_analyses: Annotated[List[RouteCostAnalysis], upsert_by_pair_index]

    # Payment methods info (set once in bulk by register_payment_methods)
    payment_methods_info: Annotated[List[PaymentMethodInfo], last_value]

    # Transport-tracking apps (set once in bulk by register_transport_apps)
    transport_apps: Annotated[List[TransportApp], last_value]

    # Path to generated PDF
    final_pdf_path: str

    # -------------------------------------------------------------------------
    # Workflow Control
    # -------------------------------------------------------------------------
    # Output language for PDF and responses
    language: str

    # Whether the entire interaction is complete
    interaction_complete: bool
