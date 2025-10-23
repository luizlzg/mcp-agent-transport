"""Tools for the transportation search agent."""
import json
import os
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from langchain_core.tools import tool
from apis.amadeus import AmadeusFlightAPI
from apis.trains import TrainAPI
from apis.buses import FlixBusAPI
from mcp_client.client import MCPFilesystemClient


def validate_date(date_str: str) -> tuple[bool, str]:
    """
    Validate date string is in YYYY-MM-DD format and in the future.

    Returns:
        (is_valid, error_message)
    """
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d")
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        if date < today:
            days_diff = (today - date).days
            return False, f"Date {date_str} is {days_diff} days in the past. Please use a future date."

        # Check if date is too far in the future (most APIs limit to ~330 days)
        max_future = today + timedelta(days=330)
        if date > max_future:
            return False, f"Date {date_str} is too far in the future (max ~330 days)"

        return True, ""
    except ValueError:
        return False, f"Invalid date format: {date_str}. Use YYYY-MM-DD (e.g., 2025-11-15)"


# Initialize API clients
flight_api = AmadeusFlightAPI()
train_api = TrainAPI()
bus_api = FlixBusAPI()

# MCP filesystem client (async operations)
# We'll create a helper function to run async operations synchronously for tool compatibility
_mcp_client = None


def get_mcp_client() -> MCPFilesystemClient:
    """Get or create MCP filesystem client."""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPFilesystemClient()
    return _mcp_client


def run_async_mcp_operation(coro):
    """
    Run an async MCP operation synchronously.
    Creates a new event loop if needed to avoid conflicts with existing loops.
    """
    try:
        # Try to get the current event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is already running, create a new one
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                return new_loop.run_until_complete(coro)
            finally:
                new_loop.close()
                asyncio.set_event_loop(loop)
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        # No event loop exists, create one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


@tool
def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    max_results: int = 3
) -> str:
    """
    Search for flights between two European cities.

    **DEPRECATION NOTICE**: Prefer using 'search_all_transport' instead of calling this directly.
    Only use this tool if search_all_transport fails or for debugging purposes.

    Args:
        origin: Origin city name or IATA code (e.g., 'Paris' or 'PAR')
        destination: Destination city name or IATA code (e.g., 'Berlin' or 'BER')
        departure_date: Departure date in YYYY-MM-DD format
        max_results: Maximum number of results to return (default: 3)

    Returns:
        JSON string with flight options including price, duration, and details
    """
    try:
        print(f"\n[TOOL] search_flights called: {origin} -> {destination} on {departure_date}")

        # Validate date
        date_valid, date_error = validate_date(departure_date)
        if not date_valid:
            return json.dumps({
                "error": "Invalid departure date",
                "message": date_error,
                "suggestion": "Use a future date in YYYY-MM-DD format"
            })

        # Check if API key is configured
        if not os.getenv('AMADEUS_API_KEY') or not os.getenv('AMADEUS_API_SECRET'):
            return json.dumps({
                "error": "Amadeus API credentials not configured",
                "message": "Please set AMADEUS_API_KEY and AMADEUS_API_SECRET in your .env file",
                "note": "Sign up at https://developers.amadeus.com/"
            })

        # Check origin and destination are different
        if origin.upper() == destination.upper():
            return json.dumps({
                "error": "Origin and destination must be different",
                "origin": origin,
                "destination": destination
            })

        # Convert city names to IATA codes if needed
        if len(origin) > 3:
            origin_code = flight_api.get_city_iata_code(origin)
            if not origin_code:
                return json.dumps({
                    "error": f"Could not find IATA code for '{origin}'",
                    "suggestion": "Try using the 3-letter airport code directly (e.g., 'PAR' for Paris, 'CDG' for Charles de Gaulle)"
                })
        else:
            origin_code = origin.upper()

        if len(destination) > 3:
            dest_code = flight_api.get_city_iata_code(destination)
            if not dest_code:
                return json.dumps({
                    "error": f"Could not find IATA code for '{destination}'",
                    "suggestion": "Try using the 3-letter airport code directly"
                })
        else:
            dest_code = destination.upper()

        print(f"[TOOL] Resolved codes: {origin_code} -> {dest_code}")

        # Search flights
        flights = flight_api.search_flights(
            origin=origin_code,
            destination=dest_code,
            departure_date=departure_date,
            max_results=max_results
        )

        if not flights:
            return json.dumps({
                "message": "No flights found or API error occurred",
                "origin": origin,
                "destination": destination,
                "date": departure_date,
                "note": "Check the console logs for detailed error messages"
            })

        print(f"[TOOL] Returning {len(flights)} flights")
        return json.dumps({
            "count": len(flights),
            "options": flights
        }, indent=2)

    except Exception as e:
        print(f"[ERROR] Tool exception: {e}")
        import traceback
        traceback.print_exc()
        return json.dumps({"error": str(e)})


@tool
def search_trains(
    origin: str,
    destination: str,
    departure_date: str,
    max_results: int = 3
) -> str:
    """
    Search for train routes between two European cities.

    **DEPRECATION NOTICE**: Prefer using 'search_all_transport' instead of calling this directly.
    Only use this tool if search_all_transport fails or for debugging purposes.

    Args:
        origin: Origin city name (e.g., 'Paris')
        destination: Destination city name (e.g., 'Berlin')
        departure_date: Departure date in YYYY-MM-DD format
        max_results: Maximum number of results to return (default: 3)

    Returns:
        JSON string with train options including price, duration, and details
    """
    try:
        trains = train_api.search_trains(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            max_results=max_results
        )

        if not trains:
            return json.dumps({
                "message": "No trains found or API key not configured",
                "note": "Set SNCF_API_KEY in .env to enable train search",
                "origin": origin,
                "destination": destination,
                "date": departure_date
            })

        return json.dumps({
            "count": len(trains),
            "options": trains
        }, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def search_buses(
    origin: str,
    destination: str,
    departure_date: str,
    max_results: int = 3
) -> str:
    """
    Search for bus routes between two European cities using FlixBus.

    **DEPRECATION NOTICE**: Prefer using 'search_all_transport' instead of calling this directly.
    Only use this tool if search_all_transport fails or for debugging purposes.

    Args:
        origin: City name (e.g., 'Paris')
        destination: Destination city name (e.g., 'Berlin')
        departure_date: Departure date in YYYY-MM-DD format
        max_results: Maximum number of results to return (default: 3)

    Returns:
        JSON string with bus options including price, duration, and details
    """
    try:
        buses = bus_api.search_buses(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            max_results=max_results
        )

        if not buses:
            return json.dumps({
                "message": "No buses found or API key not configured",
                "note": "Set RAPIDAPI_KEY in .env to enable FlixBus search",
                "origin": origin,
                "destination": destination,
                "date": departure_date
            })

        return json.dumps({
            "count": len(buses),
            "options": buses
        }, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def search_all_transport(
    origin: str,
    destination: str,
    departure_date: str
) -> str:
    """
    Search for ALL transportation options (flights, trains, AND buses) between two cities.

    **THIS IS THE PRIMARY SEARCH TOOL** - Use this for ANY route request.
    This tool automatically searches all three transport modes and returns combined results.

    IMPORTANT: After calling this tool, you MUST call 'analyze_best_routes' with the results
    to identify the cheapest and fastest options and show discarded routes.

    Workflow:
    1. Call search_all_transport(origin, destination, date)
    2. Get results with all flights, trains, and buses combined
    3. Pass results to analyze_best_routes to identify best and discarded routes
    4. Present findings to user with reasons for discarding routes

    Args:
        origin: Origin city name
        destination: Destination city name
        departure_date: Departure date in YYYY-MM-DD format

    Returns:
        JSON string with ALL transportation options (flights + trains + buses) sorted by price.
        Format: {"origin": str, "destination": str, "date": str, "total_options": int, "options": [...]}

    Example: search_all_transport("Paris", "Berlin", "2025-11-15")
             Returns ~9 routes (3 flights + 3 trains + 3 buses)
    """
    try:
        all_options = []

        # Search flights
        flights_result = search_flights.invoke({
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
            "max_results": 3
        })
        flights_data = json.loads(flights_result)
        if "options" in flights_data:
            all_options.extend(flights_data["options"])

        # Search trains
        trains_result = search_trains.invoke({
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
            "max_results": 3
        })
        trains_data = json.loads(trains_result)
        if "options" in trains_data:
            all_options.extend(trains_data["options"])

        # Search buses
        buses_result = search_buses.invoke({
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
            "max_results": 3
        })
        buses_data = json.loads(buses_result)
        if "options" in buses_data:
            all_options.extend(buses_data["options"])

        # Sort by price (handle None prices)
        all_options.sort(key=lambda x: x.get('price') or float('inf'))

        return json.dumps({
            "origin": origin,
            "destination": destination,
            "date": departure_date,
            "total_options": len(all_options),
            "options": all_options
        }, indent=2)

    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def save_itinerary(
    filename: str,
    itinerary_data: str
) -> str:
    """
    Save a travel itinerary to a file using MCP filesystem.

    Args:
        filename: Name for the saved file (without extension)
        itinerary_data: JSON string containing the itinerary data

    Returns:
        Success or error message
    """
    try:
        # Parse the itinerary data
        data = json.loads(itinerary_data)

        # Add metadata
        data['saved_at'] = datetime.now().isoformat()

        # Use MCP client to save
        async def save_operation():
            client = get_mcp_client()
            async with client:
                return await client.save_itinerary(filename, data)

        success = run_async_mcp_operation(save_operation())

        if success:
            return json.dumps({
                "status": "success",
                "message": f"Itinerary saved as {filename}.json",
                "filepath": f"./saved_itineraries/{filename}.json"
            })
        else:
            return json.dumps({
                "status": "error",
                "message": "Failed to save itinerary via MCP"
            })

    except json.JSONDecodeError as e:
        return json.dumps({
            "status": "error",
            "message": f"Invalid JSON data: {str(e)}"
        })
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"MCP save error: {str(e)}"
        })


@tool
def load_itinerary(filename: str) -> str:
    """
    Load a previously saved travel itinerary using MCP filesystem.

    Args:
        filename: Name of the file to load (without extension)

    Returns:
        JSON string with the itinerary data or error message
    """
    try:
        # Use MCP client to read
        async def read_operation():
            client = get_mcp_client()
            async with client:
                return await client.read_itinerary(filename)

        data = run_async_mcp_operation(read_operation())

        if data:
            return json.dumps(data, indent=2)
        else:
            return json.dumps({
                "status": "error",
                "message": f"Itinerary {filename} not found via MCP"
            })

    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"MCP read error: {str(e)}"
        })


@tool
def list_saved_itineraries() -> str:
    """
    List all saved itineraries using MCP filesystem.

    Returns:
        JSON string with list of saved itinerary filenames
    """
    try:
        # Use MCP client to list
        async def list_operation():
            client = get_mcp_client()
            async with client:
                return await client.list_itineraries()

        files = run_async_mcp_operation(list_operation())

        return json.dumps({
            "count": len(files),
            "itineraries": files
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"MCP list error: {str(e)}"
        })


def parse_iso_duration_to_minutes(iso_duration: str) -> float:
    """
    Parse ISO 8601 duration string to total minutes.

    Args:
        iso_duration: Duration in ISO format (e.g., 'PT2H30M')

    Returns:
        Total duration in minutes
    """
    import re
    pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?'
    match = re.match(pattern, iso_duration)

    if not match:
        return float('inf')  # Return infinity for unparseable durations

    hours = int(match.group(1)) if match.group(1) else 0
    minutes = int(match.group(2)) if match.group(2) else 0

    return hours * 60 + minutes


@tool
def analyze_best_routes(all_options_json: str) -> str:
    """
    Analyze ALL transportation routes for a trip and identify the ONE cheapest and ONE fastest route.
    Returns recommended routes AND all discarded routes with specific reasons.

    IMPORTANT: This should be called ONCE per complete route with ALL transportation options combined
    (all flights, trains, buses for that route). Do NOT call separately for each transport type.

    Args:
        all_options_json: JSON string containing ALL transportation options for a complete route.
                         Format: {"options": [option1, option2, ...]}
                         Each option should have: type, provider, price, currency, duration, origin, destination

    Returns:
        JSON string with:
        - recommended.cheapest: The ONE cheapest route (lowest price)
        - recommended.fastest: The ONE fastest route (shortest duration)
        - discarded: ALL other routes with specific reasons (e.g., "30 EUR more expensive", "2h slower")

    Example: If searching Paris→Berlin with 3 flights, 2 trains, 1 bus = 6 total routes.
             Returns: 1 cheapest route, 1 fastest route, 4-5 discarded routes (with reasons).
    """
    try:
        data = json.loads(all_options_json)

        if "options" not in data or not data["options"]:
            return json.dumps({
                "error": "No options provided to analyze",
                "message": "Please provide transportation options to analyze"
            })

        options = data["options"]

        # Filter out options without price (can't compare)
        options_with_price = [opt for opt in options if opt.get('price') is not None]

        if not options_with_price:
            return json.dumps({
                "error": "No options with valid prices",
                "message": "Cannot determine cheapest option without pricing information"
            })

        # Find cheapest option
        cheapest = min(options_with_price, key=lambda x: x['price'])

        # Find fastest option (parse duration)
        options_with_duration = [
            opt for opt in options
            if opt.get('duration') and parse_iso_duration_to_minutes(opt['duration']) != float('inf')
        ]

        fastest = None
        if options_with_duration:
            fastest = min(options_with_duration, key=lambda x: parse_iso_duration_to_minutes(x['duration']))

        # Determine discarded options with reasoning
        discarded = []
        recommended_ids = set()

        # Track which options are recommended
        if cheapest:
            recommended_ids.add(id(cheapest))
        if fastest and id(fastest) != id(cheapest):
            recommended_ids.add(id(fastest))

        # Build discarded list
        for opt in options:
            opt_id = id(opt)
            if opt_id not in recommended_ids:
                reasons = []

                # Price comparison
                if opt.get('price') is not None and cheapest:
                    price_diff = opt['price'] - cheapest['price']
                    if price_diff > 0:
                        reasons.append(f"{price_diff:.2f} {opt.get('currency', 'EUR')} more expensive than cheapest")

                # Duration comparison
                if opt.get('duration') and fastest and fastest.get('duration'):
                    opt_minutes = parse_iso_duration_to_minutes(opt['duration'])
                    fastest_minutes = parse_iso_duration_to_minutes(fastest['duration'])
                    if opt_minutes > fastest_minutes:
                        time_diff = opt_minutes - fastest_minutes
                        hours_diff = int(time_diff // 60)
                        mins_diff = int(time_diff % 60)
                        time_str = f"{hours_diff}h {mins_diff}m" if hours_diff > 0 else f"{mins_diff}m"
                        reasons.append(f"{time_str} slower than fastest")

                if not reasons:
                    reasons.append("Not the cheapest or fastest option")

                discarded.append({
                    "option": opt,
                    "reasons": reasons
                })

        result = {
            "analysis": {
                "total_options_analyzed": len(options),
                "options_with_price": len(options_with_price),
                "options_with_duration": len(options_with_duration)
            },
            "recommended": {
                "cheapest": cheapest if cheapest else None,
                "fastest": fastest if fastest else None,
                "same_option": id(cheapest) == id(fastest) if (cheapest and fastest) else False
            },
            "discarded": discarded
        }

        return json.dumps(result, indent=2)

    except json.JSONDecodeError as e:
        return json.dumps({
            "error": "Invalid JSON input",
            "message": str(e)
        })
    except Exception as e:
        return json.dumps({
            "error": "Analysis failed",
            "message": str(e)
        })


@tool
def optimize_multi_city_route(cities_json: str, departure_date: str) -> str:
    """
    Find the optimal route order for visiting multiple cities.
    Calculates ALL possible route permutations, finds cheapest and fastest complete routes,
    and shows why other route orders were discarded.

    This is for multi-city trips where you want to visit several cities and need to know
    the best ORDER to visit them in.

    Args:
        cities_json: JSON array of city names to visit (e.g., '["Paris", "Madrid", "Berlin"]')
        departure_date: Starting date in YYYY-MM-DD format

    Returns:
        JSON string with:
        - all_routes: All possible route permutations with total cost and duration
        - recommended.cheapest: The cheapest complete route order
        - recommended.fastest: The fastest complete route order
        - discarded: All other route orders with reasons why they were discarded

    Example:
        Input: ["Paris", "Madrid", "Berlin"], "2025-11-15"
        Output:
        {
            "recommended": {
                "cheapest": {
                    "route": ["Paris", "Madrid", "Berlin"],
                    "total_price": 150,
                    "total_duration_minutes": 780,
                    "legs": [...]
                },
                "fastest": {
                    "route": ["Paris", "Berlin", "Madrid"],
                    "total_price": 280,
                    "total_duration_minutes": 420,
                    "legs": [...]
                }
            },
            "discarded": [
                {
                    "route": ["Madrid", "Paris", "Berlin"],
                    "total_price": 180,
                    "reasons": ["30 EUR more expensive than cheapest", "360 minutes slower than fastest"]
                },
                ...
            ]
        }
    """
    try:
        import itertools
        from datetime import datetime, timedelta

        # Parse cities
        cities = json.loads(cities_json)

        if not isinstance(cities, list) or len(cities) < 2:
            return json.dumps({
                "error": "Need at least 2 cities to optimize route",
                "provided": cities
            })

        print(f"\n[TOOL] optimize_multi_city_route: {len(cities)} cities, starting {departure_date}")

        # Generate all permutations
        all_permutations = list(itertools.permutations(cities))
        print(f"[TOOL] Calculating {len(all_permutations)} possible routes...")

        complete_routes = []

        # For each permutation, calculate the total cost and duration
        for perm in all_permutations:
            route_cities = list(perm)
            legs = []
            total_price = 0
            total_duration_minutes = 0
            current_date = departure_date
            route_valid = True

            # Calculate each leg of this route
            for i in range(len(route_cities) - 1):
                origin = route_cities[i]
                destination = route_cities[i + 1]

                print(f"[TOOL]   Searching: {origin} -> {destination} on {current_date}")

                # Search for best option for this leg
                leg_result = search_all_transport.invoke({
                    "origin": origin,
                    "destination": destination,
                    "departure_date": current_date
                })

                leg_data = json.loads(leg_result)

                if "options" not in leg_data or not leg_data["options"]:
                    print(f"[TOOL]   No options found for {origin} -> {destination}")
                    route_valid = False
                    break

                # Pick the cheapest option for this leg
                options_with_price = [opt for opt in leg_data["options"] if opt.get('price')]
                if not options_with_price:
                    route_valid = False
                    break

                best_leg = min(options_with_price, key=lambda x: x['price'])

                legs.append({
                    "from": origin,
                    "to": destination,
                    "date": current_date,
                    "option": best_leg
                })

                total_price += best_leg.get('price', 0)
                leg_duration = parse_iso_duration_to_minutes(best_leg.get('duration', 'PT0M'))
                total_duration_minutes += leg_duration

                # Move to next day for next leg (add travel time + 1 day buffer)
                current_datetime = datetime.strptime(current_date, "%Y-%m-%d")
                next_datetime = current_datetime + timedelta(days=1)
                current_date = next_datetime.strftime("%Y-%m-%d")

            if route_valid:
                complete_routes.append({
                    "route": route_cities,
                    "total_price": total_price,
                    "total_duration_minutes": total_duration_minutes,
                    "total_duration_hours": round(total_duration_minutes / 60, 1),
                    "legs": legs
                })

        if not complete_routes:
            return json.dumps({
                "error": "Could not find valid routes for any permutation",
                "cities": cities
            })

        print(f"[TOOL] Found {len(complete_routes)} valid complete routes")

        # Find cheapest and fastest
        cheapest_route = min(complete_routes, key=lambda x: x['total_price'])
        fastest_route = min(complete_routes, key=lambda x: x['total_duration_minutes'])

        # Determine discarded routes
        discarded = []
        recommended_ids = {id(cheapest_route), id(fastest_route)}

        for route in complete_routes:
            if id(route) not in recommended_ids:
                reasons = []

                # Price comparison
                price_diff = route['total_price'] - cheapest_route['total_price']
                if price_diff > 0:
                    reasons.append(f"{price_diff:.2f} EUR more expensive than cheapest route")

                # Duration comparison
                time_diff = route['total_duration_minutes'] - fastest_route['total_duration_minutes']
                if time_diff > 0:
                    hours = int(time_diff // 60)
                    mins = int(time_diff % 60)
                    time_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"
                    reasons.append(f"{time_str} slower than fastest route")

                if not reasons:
                    reasons.append("Not the cheapest or fastest route order")

                discarded.append({
                    "route": route['route'],
                    "total_price": route['total_price'],
                    "total_duration_hours": route['total_duration_hours'],
                    "reasons": reasons
                })

        result = {
            "analysis": {
                "total_routes_analyzed": len(complete_routes),
                "cities": cities,
                "starting_date": departure_date
            },
            "recommended": {
                "cheapest": cheapest_route,
                "fastest": fastest_route,
                "same_route": (cheapest_route['route'] == fastest_route['route'])
            },
            "discarded": discarded
        }

        return json.dumps(result, indent=2)

    except json.JSONDecodeError as e:
        return json.dumps({
            "error": "Invalid JSON input for cities",
            "message": str(e)
        })
    except Exception as e:
        return json.dumps({
            "error": "Route optimization failed",
            "message": str(e)
        })
        import traceback
        traceback.print_exc()


# Export all tools
ALL_TOOLS = [
    search_flights,
    search_trains,
    search_buses,
    search_all_transport,
    analyze_best_routes,
    optimize_multi_city_route,
    save_itinerary,
    load_itinerary,
    list_saved_itineraries
]
