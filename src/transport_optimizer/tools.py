"""Tools for the transport optimizer agents.

Following LangChain 1.0 patterns:
- Tools use Command to update state directly
- Tools use ToolRuntime to access state and tool_call_id
- Handoff tools use return_direct=True to control flow
"""
import os
import json
import requests
from typing import List, Optional, Dict, Any
from langchain.tools import tool, ToolRuntime
from langchain.messages import ToolMessage
from langchain_community.utilities import GoogleSerperAPIWrapper
from langgraph.types import Command

from src.utils.logger import LOGGER


# ============================================================================
# Google Maps API Tools (Read-only, return JSON strings)
# ============================================================================
    
@tool
def search_place_coordinates(
    query: str,
    runtime: ToolRuntime,
) -> Command:
    """
    Search for place coordinates using Google Serper Places API.

    IMPORTANT: Always search in ENGLISH for best results.

    Args:
        query: Place name to search in ENGLISH. Include city/country for accuracy.
               Example: "Eiffel Tower Paris France", "Louvre Museum Paris", "Colosseum Rome Italy"

    Returns:
        A result dictionary with place details and coordinates.
    """
    serper_api_key = os.getenv("SERPER_API_KEY")
    if not serper_api_key:
        return Command(update={"messages": [ToolMessage(
            tool_call_id=runtime.tool_call_id,
            content=json.dumps({
                "error": "SERPER_API_KEY not configured. Set it in .env file for place search.",
                "found": False
            }, ensure_ascii=False, indent=2)
        )]})

    try:
        search = GoogleSerperAPIWrapper(
            serper_api_key=serper_api_key,
            type="places",
            k=3
        )

        LOGGER.info(f"Serper Places search: '{query}'")
        raw_results = search.results(query)

        # Extract places from results
        places = raw_results.get("places", [])

        if not places:
            LOGGER.warning(f"No places found for: {query}")
            return Command(update={
                "messages": [ToolMessage(
                    tool_call_id=runtime.tool_call_id,
                    content=json.dumps({
                        "query": query,
                        "found": False,
                        "message": "No places found. Try a different search query."
                    }, ensure_ascii=False, indent=2)
                )]
            })

        # Use the first (best) result
        best_place = places[0]
        latitude = best_place.get("latitude")
        longitude = best_place.get("longitude")

        if latitude is None or longitude is None:
            LOGGER.warning(f"No coordinates in place result for: {query}")
            return Command(update={
                "messages": [ToolMessage(
                    tool_call_id=runtime.tool_call_id,
                    content=json.dumps({
                        "query": query,
                        "found": False,
                        "message": "Place found but no coordinates available."
                    }, ensure_ascii=False, indent=2)
                )]
            })

        LOGGER.info(f"Found coordinates for '{query}': ({latitude}, {longitude})")

        # Build result with place info
        result = {
            "query": query,
            "found": True,
            "place": {
                "title": best_place.get("title", ""),
                "address": best_place.get("address", ""),
                "latitude": latitude,
                "longitude": longitude,
                "rating": best_place.get("rating"),
                "category": best_place.get("category", ""),
            }
        }

        # Save coordinates to state (using query as key)
        # This allows register_route_pair to retrieve coords by place name
        return Command(
            update={
                "place_coordinates": {
                    query: {
                        "lat": latitude,
                        "lon": longitude,
                        "address": best_place.get("address", ""),
                        "title": best_place.get("title", ""),
                    }
                },
                "messages": [ToolMessage(
                    tool_call_id=runtime.tool_call_id,
                    content=json.dumps(result, ensure_ascii=False, indent=2)
                )]
            },
        )

    except Exception as e:
        LOGGER.error(f"Place search error: {e}")
        return Command(update={"messages": [ToolMessage(
            tool_call_id=runtime.tool_call_id,
            content=json.dumps({
                "error": f"Place search error: {str(e)}",
                "found": False
            }, ensure_ascii=False, indent=2)
        )]})



@tool
def get_transport_options(
    start_place: str,
    end_place: str,
    runtime: ToolRuntime,
) -> str:
    """Get transport options between two places using Google Maps Directions API.

    Searches for multiple transport modes: walking, transit (subway/bus/train), and driving.
    Coordinates are automatically retrieved from the cached place_coordinates state.

    IMPORTANT: The place names must match those used in search_place_coordinates (used by route collector).

    Args:
        start_place: Name of the starting location (must exist in place_coordinates)
        end_place: Name of the destination (must exist in place_coordinates)

    Returns:
        JSON string with transport options for each mode
    """
    # Retrieve coordinates from state
    place_coordinates = runtime.state.get("place_coordinates", {})
    start_coords = place_coordinates.get(start_place)
    end_coords = place_coordinates.get(end_place)

    if not start_coords:
        return json.dumps({
            "error": f"Coordinates not found for start place: '{start_place}'.",
            "available_places": list(place_coordinates.keys())
        }, ensure_ascii=False)

    if not end_coords:
        return json.dumps({
            "error": f"Coordinates not found for end place: '{end_place}'.",
            "available_places": list(place_coordinates.keys())
        }, ensure_ascii=False)

    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        return json.dumps({
            "error": "GOOGLE_MAPS_API_KEY not configured"
        }, ensure_ascii=False)

    start_lat, start_lon = start_coords["lat"], start_coords["lon"]
    end_lat, end_lon = end_coords["lat"], end_coords["lon"]
    origin = f"{start_lat},{start_lon}"
    destination = f"{end_lat},{end_lon}"

    LOGGER.info(f"Getting transport options from {start_place} to {end_place}")

    modes_to_check = ["walking", "transit", "driving"]
    options = []

    for mode in modes_to_check:
        try:
            url = "https://maps.googleapis.com/maps/api/directions/json"
            params = {
                "origin": origin,
                "destination": destination,
                "mode": mode,
                "key": api_key,
                "alternatives": "true"
            }

            # For transit, request departure time to get real-time info
            if mode == "transit":
                import time
                params["departure_time"] = int(time.time())

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "OK" or not data.get("routes"):
                LOGGER.warning(f"No {mode} route found")
                continue

            for route in data["routes"][:2]:  # Max 2 alternatives per mode
                leg = route["legs"][0]

                # Extract duration and distance
                duration_seconds = leg["duration"]["value"]
                duration_minutes = round(duration_seconds / 60)
                distance_meters = leg["distance"]["value"]
                distance_km = round(distance_meters / 1000, 2)

                # Extract step-by-step instructions
                steps = []
                transit_details = []

                for step in leg["steps"]:
                    instruction = step.get("html_instructions", "")
                    # Clean HTML tags
                    import re
                    instruction = re.sub(r'<[^>]+>', ' ', instruction).strip()
                    steps.append(instruction)

                    # For transit, extract line information
                    if step.get("travel_mode") == "TRANSIT":
                        transit = step.get("transit_details", {})
                        line = transit.get("line", {})
                        transit_details.append({
                            "type": line.get("vehicle", {}).get("type", ""),
                            "name": line.get("short_name") or line.get("name", ""),
                            "departure_stop": transit.get("departure_stop", {}).get("name", ""),
                            "arrival_stop": transit.get("arrival_stop", {}).get("name", ""),
                            "num_stops": transit.get("num_stops", 0)
                        })

                # Build transport mode label
                if mode == "transit" and transit_details:
                    transit_types = [t["type"] for t in transit_details]
                    if "SUBWAY" in transit_types or "METRO" in transit_types:
                        mode_label = "subway"
                    elif "BUS" in transit_types:
                        mode_label = "bus"
                    elif "HEAVY_RAIL" in transit_types or "RAIL" in transit_types:
                        mode_label = "train"
                    elif "TRAM" in transit_types:
                        mode_label = "tram"
                    else:
                        mode_label = "transit"

                    # Build details string
                    details_parts = []
                    for t in transit_details:
                        if t["name"]:
                            details_parts.append(f"{t['type'].lower()} {t['name']}")
                    details = " + ".join(details_parts) if details_parts else "Public transit"
                else:
                    mode_label = mode
                    details = f"{mode.capitalize()} route"

                option = {
                    "mode": mode_label,
                    "duration_minutes": duration_minutes,
                    "distance_km": distance_km,
                    "details": details,
                    "steps": steps[:5],  # First 5 steps for brevity
                    "transit_details": transit_details if mode == "transit" else []
                }

                # Add driving-specific details
                if mode == "driving":
                    option["details"] = f"Drive via {leg.get('summary', 'main roads')}"

                options.append(option)

        except Exception as e:
            LOGGER.error(f"Error getting {mode} directions: {e}")
            continue

    result = {
        "start": start_place,
        "end": end_place,
        "options": options
    }

    return json.dumps(result, ensure_ascii=False, indent=2)


@tool
def search_transport_information(query: str) -> str:
    """Search for transport information using web search.

    The agent creates its own search query based on context.

    Example queries:
    - "Paris metro ticket price 2026"
    - "London oyster card vs contactless payment"
    - "Rome bus day pass cost"
    - "Berlin U-Bahn weekly ticket price"
    - "Madrid public transport payment methods"
    - "Rome subway supports Apple Pay"

    Args:
        query: Search query for transport pricing

    Returns:
        JSON string with search results for the agent to interpret
    """
    serper_api_key = os.getenv("SERPER_API_KEY", "")
    if not serper_api_key:
        return json.dumps({
            "error": "SERPER_API_KEY not configured"
        }, ensure_ascii=False)

    try:
        LOGGER.info(f"Searching transport pricing: '{query}'")

        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": serper_api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "q": query,
            "num": 5
        }

        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()

        # Extract relevant information from search results
        results = []
        for item in data.get("organic", [])[:5]:
            results.append({
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "link": item.get("link", "")
            })

        return json.dumps({
            "query": query,
            "results": results,
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        LOGGER.error(f"Error searching for pricing: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# ============================================================================
# State Update Tools (Return Command to update state directly)
# ============================================================================

@tool
def register_route_pair(
    start_place: str,
    end_place: str,
    start_display: str,
    end_display: str,
    pair_index: int,
    runtime: ToolRuntime,
) -> Command:
    """Register a route pair in the state.

    IMPORTANT: You must search coordinates FIRST using search_place_coordinates for both places.
    Use the EXACT SAME place names here that you used in search_place_coordinates.
    The coordinates are automatically retrieved from the cached place_coordinates state.

    Args:
        start_place: Search key (must match the query used in search_place_coordinates)
        end_place: Search key (must match the query used in search_place_coordinates)
        start_display: User-friendly name for PDF (e.g., "Eiffel Tower")
        end_display: User-friendly name for PDF (e.g., "Louvre Museum")
        pair_index: The sequence number for this route pair (0 for first, 1 for second, etc.)

    Returns:
        Command that updates state with the new route pair
    """
    # Retrieve coordinates from state
    place_coordinates = runtime.state.get("place_coordinates", {})
    start_coords = place_coordinates.get(start_place, {})
    end_coords = place_coordinates.get(end_place, {})

    if not start_coords:
        return Command(update={
            "messages": [ToolMessage(
                tool_call_id=runtime.tool_call_id,
                content=json.dumps({
                    "error": f"Coordinates not found for start place: '{start_place}'. "
                             f"Please search for it first using search_place_coordinates with the exact same name.",
                    "available_places": list(place_coordinates.keys())
                }, ensure_ascii=False, indent=2)
            )]
        })

    if not end_coords:
        return Command(update={
            "messages": [ToolMessage(
                tool_call_id=runtime.tool_call_id,
                content=json.dumps({
                    "error": f"Coordinates not found for end place: '{end_place}'. "
                             f"Please search for it first using search_place_coordinates with the exact same name.",
                    "available_places": list(place_coordinates.keys())
                }, ensure_ascii=False, indent=2)
            )]
        })

    pair = {
        "pair_index": pair_index,
        "start_place": start_place,
        "end_place": end_place,
        "start_display": start_display,
        "end_display": end_display,
        "start_coords": {"lat": start_coords["lat"], "lon": start_coords["lon"]},
        "end_coords": {"lat": end_coords["lat"], "lon": end_coords["lon"]}
    }

    LOGGER.info(f"Registered route pair: {start_place} -> {end_place}")

    return Command(update={
        "route_pairs": [pair],  # Uses operator.add reducer
        "messages": [ToolMessage(
            tool_call_id=runtime.tool_call_id,
            content=json.dumps({
                "success": True,
                "message": f"Route pair registered: {start_place} -> {end_place}",
                "pair": pair
            }, ensure_ascii=False, indent=2)
        )]
    })


@tool
def confirm_route_pairs(
    runtime: ToolRuntime,
) -> Command:
    """Confirm all route pairs are complete and hand off to transport researcher.

    Use this tool when the user has confirmed all their route pairs.
    This will transition to the transport researcher agent.

    Returns:
        Command that confirms pairs and hands off to next agent
    """
    route_pairs = runtime.state.get("route_pairs", [])

    if not route_pairs:
        return Command(update={
            "messages": [ToolMessage(
                tool_call_id=runtime.tool_call_id,
                content=json.dumps({
                    "error": "No route pairs registered. Register at least one pair first."
                }, ensure_ascii=False)
            )]
        })

    LOGGER.info(f"Route pairs confirmed: {len(route_pairs)} pairs")

    return Command(update={
        "pairs_confirmed": True,
        "next_agent": "transport_researcher",
        "current_pair_index": 0,
        "messages": [ToolMessage(
            tool_call_id=runtime.tool_call_id,
            content=json.dumps({
                "success": True,
                "message": f"All {len(route_pairs)} pairs confirmed. Moving to transport research.",
                "pairs_count": len(route_pairs)
            }, ensure_ascii=False, indent=2)
        )]
    })


@tool
def register_user_preference(
    pair_index: int,
    selected_mode: str,
    duration_minutes: int,
    distance_km: float,
    details: str,
    currency: str,
    runtime: ToolRuntime,
) -> Command:
    """Register user's transport preference for a route pair.

    IMPORTANT: Infer the appropriate currency based on the city:
    - Paris, Rome, Berlin, Madrid → EUR
    - London → GBP
    - New York, Los Angeles → USD
    - Tokyo → JPY
    - etc.

    Args:
        pair_index: Index of the route pair (0-based, so first route is 0, second is 1, etc.)
        selected_mode: The transport mode user selected (walking, subway, bus, etc.)
        duration_minutes: Duration of the selected option
        distance_km: Distance of the selected option
        details: Details of the selected option
        currency: Currency code (e.g., "EUR", "GBP", "USD") - infer based on city

    Returns:
        Command that updates state with the user preference
    """
    # Validate pair_index against actual route_pairs
    route_pairs = runtime.state.get("route_pairs", [])
    num_pairs = len(route_pairs)

    # Auto-correct 1-based indexing
    if pair_index == num_pairs and pair_index > 0:
        LOGGER.warning(f"Detected 1-based indexing in register_user_preference: pair_index={pair_index} corrected to {pair_index - 1}")
        pair_index = pair_index - 1

    if pair_index < 0 or pair_index >= num_pairs:
        return Command(update={
            "messages": [ToolMessage(
                tool_call_id=runtime.tool_call_id,
                content=json.dumps({
                    "success": False,
                    "error": f"Invalid pair_index={pair_index}. Must be 0-based index between 0 and {num_pairs - 1}. "
                             f"Use 0 for the first route, 1 for the second, etc."
                }, ensure_ascii=False)
            )]
        })

    preference = {
        "pair_index": pair_index,
        "selected_mode": selected_mode,
        "transport_details": {
            "mode": selected_mode,
            "duration_minutes": duration_minutes,
            "distance_km": distance_km,
            "currency": currency,
            "details": details,
            "steps": []
        }
    }

    LOGGER.info(f"Registered preference for pair {pair_index}: {selected_mode}")

    # Build state updates
    updates = {
        "user_preferences": [preference],  # Uses operator.add reducer
        "current_pair_index": runtime.state.get("current_pair_index", 0) + 1,
        "messages": [ToolMessage(
            tool_call_id=runtime.tool_call_id,
            content=json.dumps({
                "success": True,
                "message": f"Preference registered: {selected_mode} for pair {pair_index}",
                "preference": preference
            }, ensure_ascii=False, indent=2)
        )]
    }

    return Command(update=updates)


@tool
def finish_transport_research(
    runtime: ToolRuntime,
) -> Command:
    """Finish transport research and hand off to cost calculator.

    Use this tool when preferences have been collected for all route pairs.
    This will transition to the cost calculator agent.

    Returns:
        Command that hands off to cost calculator
    """
    user_preferences = runtime.state.get("user_preferences", [])
    route_pairs = runtime.state.get("route_pairs", [])

    LOGGER.info(f"User preferences: {user_preferences}.\nRoute pairs: {route_pairs}")

    if len(user_preferences) < len(route_pairs):
        return Command(update={
            "messages": [ToolMessage(
                tool_call_id=runtime.tool_call_id,
                content=json.dumps({
                    "error": f"Not all pairs have preferences. {len(user_preferences)}/{len(route_pairs)} collected."
                }, ensure_ascii=False)
            )]
        })

    LOGGER.info(f"Transport research finished: {len(user_preferences)} preferences")

    return Command(update={
        "all_preferences_collected": True,
        "next_agent": "cost_calculator",
        "messages": [ToolMessage(
            tool_call_id=runtime.tool_call_id,
            content=json.dumps({
                "success": True,
                "message": f"All {len(user_preferences)} preferences collected. Moving to cost calculation.",
            }, ensure_ascii=False, indent=2)
        )]
    })


@tool
def register_cost_info(
    mode: str,
    single_trip_cost: float,
    currency: str,
    runtime: ToolRuntime,
    day_pass_cost: Optional[float] = None,
    weekly_pass_cost: Optional[float] = None,
    payment_methods: Optional[List[Dict[str, Any]]] = None,
    observation: Optional[str] = None,
) -> Command:
    """Register researched cost information for a transport mode.

    Args:
        mode: Transport mode (subway, bus, train, etc.)
        single_trip_cost: Cost per single trip
        currency: Currency code (EUR, USD, GBP, etc.)
        day_pass_cost: Cost for day pass (optional)
        weekly_pass_cost: Cost for weekly pass (optional)
        payment_methods: List of payment method dicts with keys:
            - name: Payment method name
            - description: HOW to use it (where to tap, what to expect)
            - setup_required: Does user need to acquire something?
            - refillable: Can it be reused?
        observation: Discounts, special rules, notes (e.g., "Free transfers within 90 mins")

    Returns:
        Command that updates state with cost info
    """
    cost_info = {
        "mode": mode,
        "single_trip_cost": single_trip_cost,
        "day_pass_cost": day_pass_cost,
        "weekly_pass_cost": weekly_pass_cost,
        "currency": currency,
        "payment_methods": [
            {
                "name": pm.get("name", ""),
                "description": pm.get("description", ""),
                "setup_required": pm.get("setup_required", False),
                "refillable": pm.get("refillable", False)
            }
            for pm in (payment_methods or [])
        ],
        "observation": observation,
    }

    LOGGER.info(f"Registered cost info for {mode}: {single_trip_cost} {currency}/trip")

    return Command(update={
        "cost_info": {mode: cost_info},  # Uses operator.or_ reducer
        "messages": [ToolMessage(
            tool_call_id=runtime.tool_call_id,
            content=json.dumps({
                "success": True,
                "message": f"Cost info registered for {mode}",
                "cost_info": cost_info
            }, ensure_ascii=False, indent=2)
        )]
    })


@tool
def route_reasoning(
    reasoning: str,
    runtime: ToolRuntime,
) -> Command:
    """Register analysis reasoning for a route before searching prices.

    Use this to document whether a route is simple (single mode) or compound
    (multiple legs/modes) before searching for prices.

    Args:
        reasoning: Analysis of whether the route is simple or compound
    """
    LOGGER.info(f"Route reasoning registered: {reasoning[:100]}...")
    return Command(update={
        "messages": [ToolMessage(
            tool_call_id=runtime.tool_call_id,
            content=json.dumps({
                "success": True,
                "message": "Route reasoning reasoning registered. Proceed with price search."
            }, ensure_ascii=False)
        )]
    })


@tool
def register_route_cost(
    pair_index: int,
    is_compound: bool,
    modes: List[str],
    total_cost: float,
    currency: str,
    explanation: str,
    source_links: List[str],
    runtime: ToolRuntime,
    rules_applied: Optional[str] = None,
) -> Command:
    """Register the cost analysis for a specific route pair.

    After researching prices for a route, use this tool to save the cost analysis.
    Each route pair should have exactly one cost registration.

    Args:
        pair_index: Index of the route pair (0-based, so first route is 0, second is 1, etc.)
        is_compound: True if the route involves multiple legs or transport modes
        modes: List of transport modes involved (e.g., ["subway", "bus"])
        total_cost: Total cost for this route in the specified currency
        currency: Currency code (e.g., "EUR", "GBP", "USD")
        explanation: Detailed explanation of how the price was determined
        source_links: URLs where pricing information was found
        rules_applied: Transfer rules, discounts, or special pricing applied (optional)
    """
    # Validate pair_index against actual route_pairs
    route_pairs = runtime.state.get("route_pairs", [])
    num_pairs = len(route_pairs)

    # Auto-correct 1-based indexing: if pair_index equals num_pairs, assume it's 1-based
    if pair_index == num_pairs and pair_index > 0:
        LOGGER.warning(f"Detected 1-based indexing: pair_index={pair_index} corrected to {pair_index - 1}")
        pair_index = pair_index - 1

    if pair_index < 0 or pair_index >= num_pairs:
        return Command(update={
            "messages": [ToolMessage(
                tool_call_id=runtime.tool_call_id,
                content=json.dumps({
                    "success": False,
                    "error": f"Invalid pair_index={pair_index}. Must be 0-based index between 0 and {num_pairs - 1}. "
                             f"Use 0 for the first route, 1 for the second, etc."
                }, ensure_ascii=False)
            )]
        })

    if not modes:
        return Command(update={
            "messages": [ToolMessage(
                tool_call_id=runtime.tool_call_id,
                content=json.dumps({
                    "success": False,
                    "error": "The 'modes' list cannot be empty. Provide at least one transport mode."
                }, ensure_ascii=False)
            )]
        })

    if not explanation.strip():
        return Command(update={
            "messages": [ToolMessage(
                tool_call_id=runtime.tool_call_id,
                content=json.dumps({
                    "success": False,
                    "error": "The 'explanation' cannot be empty. Provide a detailed explanation of the pricing."
                }, ensure_ascii=False)
            )]
        })

    analysis = {
        "pair_index": pair_index,
        "is_compound": is_compound,
        "modes": modes,
        "total_cost": total_cost,
        "currency": currency,
        "explanation": explanation,
        "rules_applied": rules_applied,
        "source_links": source_links,
    }

    LOGGER.info(f"Registered route cost for pair {pair_index}: {total_cost} {currency}")

    return Command(update={
        "route_cost_analyses": [analysis],  # Uses operator.add reducer
        "messages": [ToolMessage(
            tool_call_id=runtime.tool_call_id,
            content=json.dumps({
                "success": True,
                "message": f"Route cost registered for pair {pair_index}: {total_cost} {currency}",
                "analysis": analysis
            }, ensure_ascii=False, indent=2)
        )]
    })


@tool
def register_payment_methods(
    payment_methods: List[Dict[str, Any]],
    runtime: ToolRuntime,
) -> Command:
    """Register all payment methods at once.

    After researching payment options, use this tool to save all payment methods.
    Each payment method dict should have: name, description, pros, cons, source_links.

    Args:
        payment_methods: List of payment method dicts, each with:
            - name: Payment method name (e.g., "Contactless", "Navigo Easy")
            - description: Step-by-step how to use it
            - pros: List of advantages
            - cons: List of disadvantages
            - source_links: List of source URLs
    """
    REQUIRED_FIELDS = ["name", "description", "pros", "cons", "source_links"]

    # Validate each payment method has all required fields
    for i, pm in enumerate(payment_methods):
        missing = [f for f in REQUIRED_FIELDS if not pm.get(f)]
        if missing:
            return Command(update={
                "messages": [ToolMessage(
                    tool_call_id=runtime.tool_call_id,
                    content=json.dumps({
                        "success": False,
                        "error": f"Payment method at index {i} is missing required fields: {', '.join(missing)}. "
                                 f"Each payment method must have all of: name, description, pros (list), cons (list), source_links (list)."
                    }, ensure_ascii=False)
                )]
            })

    methods_info = []
    for pm in payment_methods:
        methods_info.append({
            "name": pm.get("name", ""),
            "description": pm.get("description", ""),
            "pros": pm.get("pros", []),
            "cons": pm.get("cons", []),
            "source_links": pm.get("source_links", []),
        })

    LOGGER.info(f"Registered {len(methods_info)} payment methods")

    return Command(update={
        "payment_methods_info": methods_info,  # Replaces entire list (no reducer)
        "messages": [ToolMessage(
            tool_call_id=runtime.tool_call_id,
            content=json.dumps({
                "success": True,
                "message": f"Registered {len(methods_info)} payment methods.",
                "payment_methods": methods_info
            }, ensure_ascii=False, indent=2)
        )]
    })


@tool
def finish_interaction(
    runtime: ToolRuntime,
) -> Command:
    """Finish the cost calculator interaction and trigger PDF generation.

    Use this tool after you have registered all route costs and payment methods,
    and the user is satisfied. This will trigger the PDF generation node.

    Returns:
        Command that triggers pdf_generator node
    """
    # Validate completeness before allowing handoff
    route_pairs = runtime.state.get("route_pairs", [])
    route_cost_analyses = runtime.state.get("route_cost_analyses", [])
    payment_methods_info = runtime.state.get("payment_methods_info", [])

    total_pairs = len(route_pairs)
    registered_indices = {a["pair_index"] for a in route_cost_analyses}
    expected_indices = set(range(total_pairs))

    missing_costs = expected_indices - registered_indices
    if missing_costs:
        missing_str = ", ".join(str(i) for i in sorted(missing_costs))
        return Command(update={
            "messages": [ToolMessage(
                tool_call_id=runtime.tool_call_id,
                content=json.dumps({
                    "success": False,
                    "error": f"Cannot finish: route cost analyses missing for pair indices: {missing_str}. "
                             f"Registered: {len(registered_indices)}/{total_pairs} routes. "
                             f"You must call register_route_cost for every route (including walking with total_cost=0) before finishing."
                }, ensure_ascii=False)
            )]
        })

    if not payment_methods_info:
        return Command(update={
            "messages": [ToolMessage(
                tool_call_id=runtime.tool_call_id,
                content=json.dumps({
                    "success": False,
                    "error": "Cannot finish: no payment methods registered. "
                             "You must call register_payment_methods before finishing."
                }, ensure_ascii=False)
            )]
        })

    # Handoff to PDF generator
    LOGGER.info("Finishing cost calculator, handing off to pdf_generator")

    return Command(update={
        "next_agent": "pdf_generator",
        "messages": [ToolMessage(
            tool_call_id=runtime.tool_call_id,
            content=json.dumps({
                "success": True,
                "message": "Handing off to PDF generation."
            }, ensure_ascii=False)
        )]
    })


# ============================================================================
# Tool Collections by Agent
# ============================================================================

ROUTE_COLLECTOR_TOOLS = [
    search_place_coordinates,
    register_route_pair,
    confirm_route_pairs,
]

TRANSPORT_RESEARCHER_TOOLS = [
    get_transport_options,
    register_user_preference,
    finish_transport_research,
]

COST_CALCULATOR_TOOLS = [
    search_transport_information,
    route_reasoning,
    register_route_cost,
    register_payment_methods,
    finish_interaction,
]
