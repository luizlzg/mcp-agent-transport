"""Tools for the multi-agent itinerary generation graph."""
import os
import json
import requests
from bs4 import BeautifulSoup
from langchain.tools import tool, ToolRuntime
from langchain.messages import ToolMessage
from langgraph.types import Command, interrupt
from src.mcp_client.tavily_client import TavilyMCPClient
from src.utils.logger import LOGGER
from geopy.distance import geodesic
from sklearn.cluster import KMeans
from k_means_constrained import KMeansConstrained
import numpy as np


# Stock photo sites that use watermarks - exclude from search
WATERMARK_DOMAINS = [
    # Shutterstock and variants
    "shutterstock.com",
    "image.shutterstock.com",
    # Getty Images and variants
    "gettyimages.com",
    "media.gettyimages.com",
    # iStock
    "istockphoto.com",
    "media.istockphoto.com",
    # Alamy and CDN subdomains
    "alamy.com",
    "c7.alamy.com",
    "c8.alamy.com",
    "l450v.alamy.com",
    # Dreamstime
    "dreamstime.com",
    "thumbs.dreamstime.com",
    # 123RF
    "123rf.com",
    "previews.123rf.com",
    # Adobe Stock
    "stock.adobe.com",
    "t3.ftcdn.net",
    "t4.ftcdn.net",
    # Depositphotos
    "depositphotos.com",
    "st.depositphotos.com",
    "st2.depositphotos.com",
    "st3.depositphotos.com",
    # Others
    "bigstockphoto.com",
    "pond5.com",
    "vectorstock.com",
    "canstockphoto.com",
    "fotolia.com",
    "stocksy.com",
    "agefotostock.com",
    "superstock.com",
    "photoshelter.com",
    "ytimg.com",
]


# Headers for URL validation requests (avoid 403 errors)
URL_CHECK_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _check_url_accessible(url: str, timeout: int = 30) -> tuple[bool, str]:
    """
    Check if a URL is accessible.

    Args:
        url: The URL to check
        timeout: Request timeout in seconds (default: 15)

    Returns:
        Tuple of (is_accessible, error_message)
    """
    try:
        response = requests.head(url, timeout=timeout, headers=URL_CHECK_HEADERS, allow_redirects=True)
        if 200 <= response.status_code < 400:
            return True, ""
        return False, f"HTTP {response.status_code}"
    except requests.Timeout:
        return True, "Timeout, but it worked."
    except requests.RequestException as e:
        return False, str(e)


# Global clients (initialized on first use)
_tavily_client = None


def get_tavily_client():
    """Get or create Tavily MCP client."""
    global _tavily_client
    if _tavily_client is None:
        try:
            _tavily_client = TavilyMCPClient()
        except ValueError as e:
            LOGGER.warning(f"Warning: Tavily not configured: {e}")
            _tavily_client = None
    return _tavily_client


def _is_watermark_domain(url: str) -> bool:
    """Check if URL is from a known watermark/stock photo domain."""
    url_lower = url.lower()
    for domain in WATERMARK_DOMAINS:
        if domain in url_lower:
            return True
    return False


def _fetch_page_content(url: str, timeout: int = 10, max_chars: int = 1000) -> str:
    """
    Fetch and extract text content from a URL.

    Args:
        url: The URL to fetch
        timeout: Request timeout in seconds
        max_chars: Maximum characters to return (to avoid huge responses)

    Returns:
        Extracted text content or error message
    """
    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers=URL_CHECK_HEADERS,
            allow_redirects=True
        )
        response.raise_for_status()

        # Parse HTML and extract text
        soup = BeautifulSoup(response.text, 'html.parser')

        # Remove script and style elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            element.decompose()

        # Get text content
        text = soup.get_text(separator='\n', strip=True)

        # Clean up multiple newlines
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        text = '\n'.join(lines)

        # Truncate if too long
        if len(text) > max_chars:
            text = text[:max_chars] + "..."

        return text

    except requests.Timeout:
        return "[Error: Request timeout]"
    except requests.RequestException as e:
        return f"[Error: {str(e)}]"
    except Exception as e:
        return f"[Error parsing page: {str(e)}]"


@tool
def search_attraction_info(
    query: str,
) -> str:
    """
    Web search tool to find information about attractions using Google Search.
    Fetches full page content from search results.

    Args:
        query: Search query

    Returns:
        JSON string with search results (5 results) including full page content
    """
    serper_api_key = os.getenv("SERPER_API_KEY")
    if not serper_api_key:
        return json.dumps({
            "error": "SERPER_API_KEY not configured. Set it in .env file",
        }, ensure_ascii=False)

    try:
        from langchain_community.utilities import GoogleSerperAPIWrapper

        search = GoogleSerperAPIWrapper(
            serper_api_key=serper_api_key,
            type="search",
            k=5
        )

        LOGGER.info(f"SERP search for attraction info: '{query}'")
        raw_results = search.results(query)

        # Extract organic results
        organic = raw_results.get("organic", [])

        tool_output = []
        for res in organic[:3]:
            url = res.get("link", "")
            title = res.get("title", "")

            # Fetch full page content
            LOGGER.info(f"Fetching content from: {url}")
            content = _fetch_page_content(url)

            tool_output.append({
                "url": url,
                "title": title,
                "snippet": res.get("snippet", ""),
                "content": content
            })

        return json.dumps(tool_output, ensure_ascii=False, indent=2)

    except Exception as e:
        LOGGER.error(f"SERP search error: {e}")
        return json.dumps({
            "error": f"Search error: {str(e)}",
        }, ensure_ascii=False)


@tool
def search_attraction_images(
    query: str,
    count: int = 10
) -> str:
    """
    Search for high-quality images of a tourist attraction using Tavily.

    Makes multiple searches with query variations to get more images,
    since Tavily typically returns only 5-10 images per search.

    Automatically validates image URLs and filters out broken/inaccessible links
    before returning results.

    Args:
        query: Search query (attraction name, city, etc.)
        count: Number of images to fetch (default: 10)

    Returns:
        JSON string with validated image URLs. Includes metadata:
        - images_found: Total images found from search
        - images_valid: Number of accessible images returned
        - images_filtered: Number of broken images filtered out
        - images: List of accessible image URLs with descriptions
    """
    client = get_tavily_client()
    if not client:
        return json.dumps({
            "error": "Tavily not configured. Set TAVILY_API_KEY in .env file",
        }, ensure_ascii=False)

    try:
        # Multiple query variations to get more images (Tavily returns ~5 per search)
        query_variations = [
            query,
            f"{query} photos",
            f"{query} landmark tourist attraction",
        ]

        all_images = []
        seen_urls = set()

        for q in query_variations:
            search_data = client.search(
                q,
                max_results=5,
                search_depth="advanced",
                include_images=True,
                include_image_descriptions=True,
                exclude_domains=WATERMARK_DOMAINS,
            )

            images = search_data.get("images", [])

            # Filter and deduplicate
            for img in images:
                url = img.get("url", "")
                if url and url not in seen_urls and not _is_watermark_domain(url):
                    seen_urls.add(url)
                    all_images.append(img)

            # Stop if we have enough images
            if len(all_images) >= count:
                break

        # Validate image URLs and filter out broken ones
        valid_images = []
        broken_count = 0

        LOGGER.info(f"Validating {min(len(all_images), count)} image URLs for accessibility...")

        for img_object in all_images[:count]:
            url = img_object.get("url", "")

            # Check if URL is accessible
            is_accessible, error_message = _check_url_accessible(url, timeout=5)

            if is_accessible:
                valid_images.append(img_object)
                LOGGER.info(f"✅ Image URL accessible: {url}")
            else:
                broken_count += 1
                LOGGER.warning(f"❌ Image URL broken (filtered out): {url} - {error_message}")

        # Build result with only valid images
        result = {
            "images_found": len(all_images),
            "images_valid": len(valid_images),
            "images_filtered": broken_count,
            "images": []
        }

        for img_object in valid_images:
            result["images"].append({
                "url_regular": img_object.get("url", ""),
                "description": img_object.get("description", ""),
            })

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        return json.dumps({
            "error": f"Image search error: {str(e)}",
        }, ensure_ascii=False)


# Third-party ticket reseller domains to filter out
TICKET_RESELLER_DOMAINS = [
    "tripadvisor.com",
    "viator.com",
    "getyourguide.com",
    "tiqets.com",
    "klook.com",
    "booking.com",
    "expedia.com",
    "musement.com",
    "headout.com",
    "civitatis.com",
    "ticketmaster.com",
]


def _is_ticket_reseller(url: str) -> bool:
    """Check if URL is from a known ticket reseller domain."""
    url_lower = url.lower()
    for domain in TICKET_RESELLER_DOMAINS:
        if domain in url_lower:
            return True
    return False


@tool
def search_ticket_link(query: str) -> str:
    """
    Search for ticket purchase links using Google Search (Serper).

    Use this tool to find official ticket/booking pages for attractions.
    You control the search query - craft it to find official ticket pages.

    The tool automatically validates that URLs are accessible and filters out broken links.
    Only working URLs are returned.

    Args:
        query: Search query to find ticket links. Examples:
               - "buy tickets Colosseum Rome official"
               - "Louvre Museum Paris billets site officiel"
               - "Vatican Museums tickets official website"
               - "biglietti Musei Vaticani sito ufficiale"

    Returns:
        JSON with validated, working ticket page URLs.
        Results from third-party resellers (TripAdvisor, Viator, etc.) are filtered out.
        Only accessible URLs (HTTP 200-399) are included.
    """
    serper_api_key = os.getenv("SERPER_API_KEY")
    if not serper_api_key:
        return json.dumps({
            "error": "SERPER_API_KEY not configured. Set it in .env file.",
        }, ensure_ascii=False, indent=2)

    try:
        from langchain_community.utilities import GoogleSerperAPIWrapper

        search = GoogleSerperAPIWrapper(
            serper_api_key=serper_api_key,
            type="search",
            k=15  # Get more results to have enough after filtering and validation
        )

        LOGGER.info(f"Serper ticket search: '{query}'")
        raw_results = search.results(query)

        # Extract organic results
        organic_results = raw_results.get("organic", [])

        # Filter out reseller domains, validate URLs, and format results
        validated_results = []
        checked_count = 0

        for result in organic_results:
            url = result.get("link", "")

            # Skip reseller domains
            if not url or _is_ticket_reseller(url):
                continue

            checked_count += 1
            LOGGER.info(f"Validating ticket URL ({checked_count}): {url}")

            # Validate URL is accessible
            is_accessible, error_message = _check_url_accessible(url)

            if is_accessible:
                validated_results.append({
                    "title": result.get("title", ""),
                    "url": url,
                    "snippet": result.get("snippet", ""),
                })
                LOGGER.info(f"✅ Valid ticket URL: {url}")

                # Stop after 3 valid results
                if len(validated_results) >= 3:
                    break
            else:
                LOGGER.info(f"❌ Invalid ticket URL: {url} - {error_message}")

            # Don't check too many URLs to avoid slowdown
            if checked_count >= 8:
                break

        if not validated_results:
            return json.dumps({
                "results": [],
                "message": "No working official ticket pages found. Try a different search query (e.g., in local language, or with 'official site')."
            }, ensure_ascii=False, indent=2)

        return json.dumps({
            "results": validated_results,
            "message": f"Found {len(validated_results)} working official ticket page(s). Use the URL from the most official-looking domain."
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        LOGGER.error(f"Ticket link search error: {e}")
        return json.dumps({
            "error": f"Search error: {str(e)}",
        }, ensure_ascii=False, indent=2)


@tool
def search_place_address(
    original_name: str,
    query: str,
    runtime: ToolRuntime,
) -> Command:
    """
    Search for the official address of a place using Google Places and store coordinates.

    This tool searches for attractions and AUTOMATICALLY stores the coordinates in state.
    The coordinates are stored with the original_name as key, preserving the user's language.

    IMPORTANT: Always search in ENGLISH for best results.

    Args:
        original_name: The attraction name as the user wrote it (in their language).
                       This will be used as the key when storing coordinates.
                       Example: "Torre Eiffel", "Museu do Louvre", "Coliseu"
        query: Place name to search in ENGLISH. Include city/country for accuracy.
               Example: "Eiffel Tower Paris France", "Louvre Museum Paris", "Colosseum Rome Italy"

    Returns:
        Command that updates state with coordinates and returns place info
    """
    serper_api_key = os.getenv("SERPER_API_KEY")
    if not serper_api_key:
        return Command(update={"messages": [ToolMessage(
            tool_call_id=runtime.tool_call_id,
            content=json.dumps({
                "error": "SERPER_API_KEY not configured. Set it in .env file for place search.",
                "original_name": original_name,
                "found": False
            }, ensure_ascii=False, indent=2)
        )]})

    try:
        from langchain_community.utilities import GoogleSerperAPIWrapper

        search = GoogleSerperAPIWrapper(
            serper_api_key=serper_api_key,
            type="places",
            k=3
        )

        LOGGER.info(f"Serper Places search: '{query}' for attraction '{original_name}'")
        raw_results = search.results(query)

        # Extract places from results
        places = raw_results.get("places", [])

        if not places:
            LOGGER.warning(f"No places found for: {query}")
            return Command(update={
                "failed_coordinate_lookups": [original_name],  # Track the failure
                "messages": [ToolMessage(
                    tool_call_id=runtime.tool_call_id,
                    content=json.dumps({
                        "original_name": original_name,
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
                "failed_coordinate_lookups": [original_name],  # Track the failure
                "messages": [ToolMessage(
                    tool_call_id=runtime.tool_call_id,
                    content=json.dumps({
                        "original_name": original_name,
                        "query": query,
                        "found": False,
                        "message": "Place found but no coordinates available."
                    }, ensure_ascii=False, indent=2)
                )]
            })

        LOGGER.info(f"Found coordinates for '{original_name}': ({latitude}, {longitude})")

        # Build result with place info
        result = {
            "original_name": original_name,
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

        # Update state with coordinates (using original_name as key)
        return Command(
            update={
                "attraction_coordinates": {
                    original_name: {
                        "lat": latitude,
                        "lon": longitude
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
                "original_name": original_name,
                "found": False
            }, ensure_ascii=False, indent=2)
        )]})


def _calculate_centroid(coordinates: dict, names: list) -> tuple:
    """Calculate the centroid (center point) for a list of attractions."""
    if not names:
        return None
    lats = [coordinates[name]["lat"] for name in names if name in coordinates]
    lons = [coordinates[name]["lon"] for name in names if name in coordinates]
    if not lats:
        return None
    return (sum(lats) / len(lats), sum(lons) / len(lons))


def _order_attractions_nearest_neighbor(
    coordinates: dict,
    attractions: list,
    starting_point: str = None,
    ending_point: str = None
) -> list:
    """
    Order attractions using nearest-neighbor algorithm.

    Algorithm:
    1. If ending_point is provided and valid, reserve it (remove from pool)
    2. If starting_point is provided and valid, use it as the first attraction
    3. Otherwise, calculate the center (centroid) and start from the closest attraction to it
    4. From the current attraction, go to the nearest unvisited attraction
    5. Repeat until all attractions are visited
    6. Append ending_point at the end (if it was reserved)

    Args:
        coordinates: Dict with {name: {lat, lon}} for each attraction
        attractions: List of attraction names to order
        starting_point: Optional attraction name to start the route from
        ending_point: Optional attraction name to end the route at

    Returns:
        Ordered list of attraction names
    """
    if len(attractions) <= 1:
        return attractions

    # Filter attractions that have coordinates
    attractions_with_coords = [a for a in attractions if a in coordinates]
    if len(attractions_with_coords) <= 1:
        return attractions

    def distance_to_point(name, point):
        coord = (coordinates[name]["lat"], coordinates[name]["lon"])
        return geodesic(coord, point).km

    # Reserve ending point if valid (remove from pool to append at the end)
    reserved_ending = None
    if ending_point and ending_point in attractions_with_coords:
        # Don't reserve if ending_point == starting_point (circular route handled naturally)
        if ending_point != starting_point:
            reserved_ending = ending_point
            attractions_with_coords = [a for a in attractions_with_coords if a != ending_point]
            LOGGER.info(f"Reserved ending point: {ending_point}")

    # If after reserving ending, we have 0 or 1 attractions left
    if len(attractions_with_coords) <= 1:
        result = attractions_with_coords[:]
        if reserved_ending:
            result.append(reserved_ending)
        # Add any attractions without coordinates at the end
        attractions_without_coords = [a for a in attractions if a not in coordinates]
        result.extend(attractions_without_coords)
        return result

    # Determine starting point
    if starting_point and starting_point in attractions_with_coords:
        # User specified a valid starting point
        first_attraction = starting_point
        LOGGER.info(f"Using user-specified starting point: {starting_point}")
    else:
        # Default: find attraction closest to centroid
        centroid = _calculate_centroid(coordinates, attractions_with_coords)
        if not centroid:
            if reserved_ending:
                return attractions_with_coords + [reserved_ending]
            return attractions
        first_attraction = min(attractions_with_coords, key=lambda a: distance_to_point(a, centroid))
        LOGGER.info(f"Using centroid-based starting point: {first_attraction}")

    # Nearest-neighbor traversal
    ordered = [first_attraction]
    remaining = set(attractions_with_coords) - {first_attraction}

    while remaining:
        current = ordered[-1]
        current_coord = (coordinates[current]["lat"], coordinates[current]["lon"])

        # Find nearest unvisited attraction
        nearest = min(remaining, key=lambda a: distance_to_point(a, current_coord))
        ordered.append(nearest)
        remaining.remove(nearest)

    # Append reserved ending point at the end
    if reserved_ending:
        ordered.append(reserved_ending)

    # Add any attractions without coordinates at the end
    attractions_without_coords = [a for a in attractions if a not in coordinates]
    ordered.extend(attractions_without_coords)

    return ordered


def _validate_day_assignments(assignments: dict, num_days: int, param_name: str) -> tuple[bool, str]:
    """Validate day assignments are integers within valid range."""
    for name, day in assignments.items():
        if not isinstance(day, int):
            return False, f"{param_name}: day for '{name}' must be integer, got {type(day).__name__}"
        if day < 1:
            return False, f"{param_name}: day for '{name}' must be >= 1, got {day}"
        if day > num_days:
            return False, f"{param_name}: day for '{name}' must be <= {num_days}, got {day}"
    return True, ""


# ============================================================================
# New 3-Step Workflow Tools
# ============================================================================

@tool
def classify_attractions(
    runtime: ToolRuntime,
    classifications: list[dict],
    exclusive_days: list[int] = None,
) -> Command:
    """
    Step 1 of the 3-step workflow: Classify each attraction before organization.

    This tool validates attraction classifications and stores them in state
    for use by finalize_day_organization.

    IMPORTANT: Call this AFTER getting coordinates for all attractions.

    Args:
        classifications: List of classification objects. Each object must have:
            - name: str - Attraction name (must match coordinates key)
            - type: "isolated" | "preference" | "flexible"
                - isolated: Needs exclusive day (e.g., Disneyland, day trips)
                - preference: Must be on specific day but can share
                - flexible: Let system optimize by geography (K-means)
            - day: int | None - Required for isolated/preference, null for flexible

            Example:
            [
                {"name": "Disneyland", "type": "isolated", "day": 3},
                {"name": "Eiffel Tower", "type": "preference", "day": 1},
                {"name": "Louvre", "type": "flexible", "day": null}
            ]

        exclusive_days: Optional list of day numbers that should NOT receive
            flexible attractions from K-means. Use when the user explicitly
            defines the complete set of attractions for a day.
            Example: [3] means day 3 is closed to flexible additions.

    Returns:
        Command that stores validated classifications in state.
        On error, returns specific feedback about what's wrong.
    """
    try:
        # Check if itinerary was already approved
        if runtime.state.get("itinerary_approved", False):
            return Command(update={
                "messages": [ToolMessage(
                    json.dumps({
                        "error": "CANNOT RECLASSIFY: The itinerary has already been approved. "
                                 "Use 'update_itinerary_organization' for post-approval changes."
                    }, ensure_ascii=False),
                    tool_call_id=runtime.tool_call_id
                )]
            })

        num_days = runtime.state.get("num_days")
        coordinates = runtime.state.get("attraction_coordinates", {})
        failed_lookups = runtime.state.get("failed_coordinate_lookups", [])

        # Filter out failures that were corrected by retry
        unresolved_failures = [name for name in failed_lookups if name not in coordinates]
        if unresolved_failures:
            return Command(update={
                "messages": [ToolMessage(
                    json.dumps({
                        "error": f"Failed to get coordinates for: {unresolved_failures}. "
                                 f"Retry search_place_address with different queries for these attractions."
                    }, ensure_ascii=False),
                    tool_call_id=runtime.tool_call_id
                )]
            })

        if not coordinates:
            return Command(update={
                "messages": [ToolMessage(
                    json.dumps({
                        "error": "No coordinates found. Call search_place_address for each attraction first."
                    }, ensure_ascii=False),
                    tool_call_id=runtime.tool_call_id
                )]
            })

        if not classifications:
            return Command(update={
                "messages": [ToolMessage(
                    json.dumps({
                        "error": "classifications list is empty. Classify ALL attractions."
                    }, ensure_ascii=False),
                    tool_call_id=runtime.tool_call_id
                )]
            })

        # Validate classifications structure
        valid_types = {"isolated", "preference", "flexible"}
        classified_attractions = {}
        isolated_days_used = {}  # Track which days are reserved for isolated attractions
        errors = []

        for idx, c in enumerate(classifications):
            if not isinstance(c, dict):
                errors.append(f"Classification {idx} must be an object, got {type(c).__name__}")
                continue

            name = c.get("name")
            ctype = c.get("type")
            day = c.get("day")

            # Validate name exists
            if not name:
                errors.append(f"Classification {idx} missing 'name' field")
                continue

            # Validate name matches a known attraction
            if name not in coordinates:
                errors.append(f"Attraction '{name}' not found in coordinates. Check the name spelling.")
                continue

            # Validate type
            if ctype not in valid_types:
                errors.append(f"Attraction '{name}': type must be one of {valid_types}, got '{ctype}'")
                continue

            # Validate day for isolated/preference types
            if ctype in ("isolated", "preference"):
                if day is None:
                    errors.append(f"Attraction '{name}': type='{ctype}' requires a day number, got null")
                    continue
                if not isinstance(day, int):
                    errors.append(f"Attraction '{name}': day must be integer, got {type(day).__name__}")
                    continue
                if day < 1 or day > num_days:
                    errors.append(f"Attraction '{name}': day {day} is out of range [1, {num_days}]")
                    continue

                # Track isolated days
                if ctype == "isolated":
                    if day in isolated_days_used:
                        errors.append(
                            f"Attraction '{name}': day {day} is already isolated for '{isolated_days_used[day]}'. "
                            f"Each isolated attraction needs a unique day."
                        )
                        continue
                    isolated_days_used[day] = name

            # Validate flexible attractions don't have a day
            if ctype == "flexible" and day is not None:
                errors.append(f"Attraction '{name}': type='flexible' should have day=null, got {day}")
                continue

            classified_attractions[name] = {"type": ctype, "day": day}

        # Check all attractions are classified
        missing = set(coordinates.keys()) - set(classified_attractions.keys())
        if missing:
            errors.append(f"Missing classifications for: {list(missing)}")

        # Check for preference conflicts with isolated days
        for name, info in classified_attractions.items():
            if info["type"] == "preference" and info["day"] in isolated_days_used:
                isolated_name = isolated_days_used[info["day"]]
                errors.append(
                    f"Attraction '{name}' has preference for day {info['day']}, "
                    f"but that day is isolated for '{isolated_name}'. Move '{name}' to a different day."
                )

        # Validate exclusive_days
        validated_exclusive_days = []
        if exclusive_days:
            for ed in exclusive_days:
                if not isinstance(ed, int):
                    errors.append(f"exclusive_days: each day must be integer, got {type(ed).__name__}")
                    continue
                if ed < 1 or ed > num_days:
                    errors.append(f"exclusive_days: day {ed} is out of range [1, {num_days}]")
                    continue
                if ed in isolated_days_used:
                    errors.append(
                        f"exclusive_days: day {ed} is already isolated for '{isolated_days_used[ed]}'. "
                        f"Isolated days are exclusive by nature, no need to add them to exclusive_days."
                    )
                    continue
                # Check that exclusive day has at least one preference attraction
                day_has_preference = any(
                    info["type"] == "preference" and info["day"] == ed
                    for info in classified_attractions.values()
                )
                if not day_has_preference:
                    errors.append(
                        f"exclusive_days: day {ed} has no preference attractions assigned. "
                        f"An exclusive day must have at least one preference attraction."
                    )
                    continue
                validated_exclusive_days.append(ed)

        if errors:
            return Command(update={
                "messages": [ToolMessage(
                    json.dumps({
                        "error": "Classification validation failed",
                        "details": errors
                    }, ensure_ascii=False, indent=2),
                    tool_call_id=runtime.tool_call_id
                )]
            })

        # Store classifications in state
        LOGGER.info(f"Classifications validated: {len(classified_attractions)} attractions, exclusive_days={validated_exclusive_days}")

        return Command(update={
            "attraction_classifications": classified_attractions,
            "exclusive_days": validated_exclusive_days,
            "messages": [ToolMessage(
                json.dumps({
                    "success": True,
                    "message": "Classifications validated and stored. "
                               "Next: optionally call configure_route_optimization, then call finalize_day_organization.",
                    "summary": {
                        "isolated": [n for n, i in classified_attractions.items() if i["type"] == "isolated"],
                        "preference": [n for n, i in classified_attractions.items() if i["type"] == "preference"],
                        "flexible": [n for n, i in classified_attractions.items() if i["type"] == "flexible"],
                        "exclusive_days": validated_exclusive_days,
                    }
                }, ensure_ascii=False, indent=2),
                tool_call_id=runtime.tool_call_id
            )]
        })

    except Exception as e:
        LOGGER.error(f"Error in classify_attractions: {e}", exc_info=True)
        return Command(update={
            "messages": [ToolMessage(
                json.dumps({"error": f"Error: {str(e)}"}, ensure_ascii=False),
                tool_call_id=runtime.tool_call_id
            )]
        })


@tool
def configure_route_optimization(
    runtime: ToolRuntime,
    optimize_by_distance: bool = False,
    starting_points: dict[str, str] = None,
    ending_points: dict[str, str] = None,
) -> Command:
    """
    Step 2 of the 3-step workflow (OPTIONAL): Configure route optimization settings.

    This tool validates and stores route optimization preferences for use by
    finalize_day_organization. Only call this if you need distance optimization
    or specific start/end points.

    IMPORTANT: Call this AFTER classify_attractions, BEFORE finalize_day_organization.

    Args:
        optimize_by_distance: If True, order attractions within each day by
                              geographic proximity (nearest-neighbor algorithm).
                              Default: False (preserve input order).

        starting_points: Dict specifying where to START each day's route.
                         Format: {"Day 1": "Colosseum", "Day 2": "Vatican Museums"}
                         The attraction MUST be assigned to that day in classifications.

        ending_points: Dict specifying where to END each day's route.
                       Format: {"Day 1": "Palatine Hill", "Day 2": "Castel Sant'Angelo"}
                       The attraction MUST be assigned to that day in classifications.

    Returns:
        Command that stores validated config in state.
        On error, returns specific feedback about what's wrong.
    """
    try:
        # Check if itinerary was already approved
        if runtime.state.get("itinerary_approved", False):
            return Command(update={
                "messages": [ToolMessage(
                    json.dumps({
                        "error": "CANNOT RECONFIGURE: The itinerary has already been approved."
                    }, ensure_ascii=False),
                    tool_call_id=runtime.tool_call_id
                )]
            })

        # Get classifications from state
        classifications = runtime.state.get("attraction_classifications", {})
        if not classifications:
            return Command(update={
                "messages": [ToolMessage(
                    json.dumps({
                        "error": "No classifications found. Call classify_attractions first."
                    }, ensure_ascii=False),
                    tool_call_id=runtime.tool_call_id
                )]
            })

        num_days = runtime.state.get("num_days")
        errors = []

        # Validate starting_points
        if starting_points:
            for day_label, attraction in starting_points.items():
                # Parse day number from label (e.g., "Day 1" -> 1)
                try:
                    day_num = int(day_label.split()[-1])
                except (ValueError, IndexError):
                    errors.append(f"starting_points: Invalid day label '{day_label}'. Use format 'Day N'.")
                    continue

                if day_num < 1 or day_num > num_days:
                    errors.append(f"starting_points: Day {day_num} is out of range [1, {num_days}]")
                    continue

                # Check attraction exists and is assigned to this day
                if attraction not in classifications:
                    errors.append(
                        f"starting_points: '{attraction}' not found in classifications. "
                        f"Check the name spelling."
                    )
                    continue

                classified = classifications[attraction]
                if classified["type"] == "flexible":
                    errors.append(
                        f"starting_points: '{attraction}' is flexible (no assigned day). "
                        f"To use it as a starting point, first classify it with type='preference' and day={day_num}."
                    )
                elif classified["day"] != day_num:
                    errors.append(
                        f"starting_points: '{attraction}' is assigned to day {classified['day']}, "
                        f"but you specified it as starting point for {day_label}. "
                        f"The attraction must be assigned to the same day."
                    )

        # Validate ending_points
        if ending_points:
            for day_label, attraction in ending_points.items():
                try:
                    day_num = int(day_label.split()[-1])
                except (ValueError, IndexError):
                    errors.append(f"ending_points: Invalid day label '{day_label}'. Use format 'Day N'.")
                    continue

                if day_num < 1 or day_num > num_days:
                    errors.append(f"ending_points: Day {day_num} is out of range [1, {num_days}]")
                    continue

                if attraction not in classifications:
                    errors.append(
                        f"ending_points: '{attraction}' not found in classifications."
                    )
                    continue

                classified = classifications[attraction]
                if classified["type"] == "flexible":
                    errors.append(
                        f"ending_points: '{attraction}' is flexible (no assigned day). "
                        f"To use it as an ending point, first classify it with type='preference' and day={day_num}."
                    )
                elif classified["day"] != day_num:
                    errors.append(
                        f"ending_points: '{attraction}' is assigned to day {classified['day']}, "
                        f"but you specified it as ending point for {day_label}."
                    )

        if errors:
            return Command(update={
                "messages": [ToolMessage(
                    json.dumps({
                        "error": "Route optimization validation failed",
                        "details": errors
                    }, ensure_ascii=False, indent=2),
                    tool_call_id=runtime.tool_call_id
                )]
            })

        # Store config in state
        config = {
            "enabled": optimize_by_distance,
            "starting_points": starting_points or {},
            "ending_points": ending_points or {},
        }

        LOGGER.info(f"Route optimization config validated: {config}")

        return Command(update={
            "route_optimization_config": config,
            "messages": [ToolMessage(
                json.dumps({
                    "success": True,
                    "message": "Route optimization configured. Next: call finalize_day_organization.",
                    "config": config
                }, ensure_ascii=False, indent=2),
                tool_call_id=runtime.tool_call_id
            )]
        })

    except Exception as e:
        LOGGER.error(f"Error in configure_route_optimization: {e}", exc_info=True)
        return Command(update={
            "messages": [ToolMessage(
                json.dumps({"error": f"Error: {str(e)}"}, ensure_ascii=False),
                tool_call_id=runtime.tool_call_id
            )]
        })


@tool
def configure_day_constraints(
    runtime: ToolRuntime,
    min_attractions_per_day: int = None,
    max_attractions_per_day: int = None,
) -> Command:
    """
    OPTIONAL: Configure min/max attractions per day for K-means clustering.

    ONLY use this tool if the user EXPLICITLY requests min or max constraints
    (e.g., "max 3 per day", "at least 2 per day"). Do NOT use if no constraints are mentioned.

    Must be called AFTER classify_attractions and BEFORE finalize_day_organization.

    Args:
        min_attractions_per_day: Minimum number of attractions per day (must be >= 1).
        max_attractions_per_day: Maximum number of attractions per day (must be >= 1).
    """
    try:
        # Validate at least one constraint is provided
        if min_attractions_per_day is None and max_attractions_per_day is None:
            return Command(update={
                "messages": [ToolMessage(
                    json.dumps({
                        "error": "At least one constraint must be provided: min_attractions_per_day or max_attractions_per_day."
                    }, ensure_ascii=False),
                    tool_call_id=runtime.tool_call_id
                )]
            })

        # Validate min
        if min_attractions_per_day is not None and min_attractions_per_day < 1:
            return Command(update={
                "messages": [ToolMessage(
                    json.dumps({
                        "error": "min_attractions_per_day must be >= 1."
                    }, ensure_ascii=False),
                    tool_call_id=runtime.tool_call_id
                )]
            })

        # Validate max
        if max_attractions_per_day is not None and max_attractions_per_day < 1:
            return Command(update={
                "messages": [ToolMessage(
                    json.dumps({
                        "error": "max_attractions_per_day must be >= 1."
                    }, ensure_ascii=False),
                    tool_call_id=runtime.tool_call_id
                )]
            })

        # Validate min <= max
        if (min_attractions_per_day is not None and max_attractions_per_day is not None
                and min_attractions_per_day > max_attractions_per_day):
            return Command(update={
                "messages": [ToolMessage(
                    json.dumps({
                        "error": f"min_attractions_per_day ({min_attractions_per_day}) cannot be greater than max_attractions_per_day ({max_attractions_per_day})."
                    }, ensure_ascii=False),
                    tool_call_id=runtime.tool_call_id
                )]
            })

        # Check classifications exist
        classifications = runtime.state.get("attraction_classifications", {})
        if not classifications:
            return Command(update={
                "messages": [ToolMessage(
                    json.dumps({
                        "error": "No classifications found. Call classify_attractions first, then configure_day_constraints."
                    }, ensure_ascii=False),
                    tool_call_id=runtime.tool_call_id
                )]
            })

        config = {
            "min_per_day": min_attractions_per_day,
            "max_per_day": max_attractions_per_day,
        }

        LOGGER.info(f"Day constraints config validated: {config}")

        return Command(update={
            "day_constraints_config": config,
            "messages": [ToolMessage(
                json.dumps({
                    "success": True,
                    "message": "Day constraints configured. Next: call finalize_day_organization.",
                    "config": config
                }, ensure_ascii=False, indent=2),
                tool_call_id=runtime.tool_call_id
            )]
        })

    except Exception as e:
        LOGGER.error(f"Error in configure_day_constraints: {e}", exc_info=True)
        return Command(update={
            "messages": [ToolMessage(
                json.dumps({"error": f"Error: {str(e)}"}, ensure_ascii=False),
                tool_call_id=runtime.tool_call_id
            )]
        })


@tool
def finalize_day_organization(
    runtime: ToolRuntime,
) -> Command:
    """
    Step 3 of the 3-step workflow: Execute organization using validated state.

    This tool reads classifications and optimization config from state, then:
    1. Places isolated attractions on their exclusive days
    2. Places preference attractions on their specified days
    3. Runs K-means on flexible attractions to group by geography
    4. Applies distance optimization if configured

    IMPORTANT: Call this AFTER classify_attractions (and optionally configure_route_optimization).

    Returns:
        Command that updates state with organized_days and clusters.
        Sets has_flexible_attractions=True if K-means was used (requires approval).
    """
    try:
        # Check if itinerary was already approved
        if runtime.state.get("itinerary_approved", False):
            return Command(update={
                "messages": [ToolMessage(
                    json.dumps({
                        "error": "CANNOT REORGANIZE: The itinerary has already been approved. "
                                 "Use 'update_itinerary_organization' for post-approval changes."
                    }, ensure_ascii=False),
                    tool_call_id=runtime.tool_call_id
                )]
            })

        # Get state
        num_days = runtime.state.get("num_days")
        coordinates = runtime.state.get("attraction_coordinates", {})
        classifications = runtime.state.get("attraction_classifications", {})
        optimization_config = runtime.state.get("route_optimization_config", {})

        if not classifications:
            return Command(update={
                "messages": [ToolMessage(
                    json.dumps({
                        "error": "No classifications found. Call classify_attractions first."
                    }, ensure_ascii=False),
                    tool_call_id=runtime.tool_call_id
                )]
            })

        if not coordinates:
            return Command(update={
                "messages": [ToolMessage(
                    json.dumps({
                        "error": "No coordinates found. This shouldn't happen if classify_attractions succeeded."
                    }, ensure_ascii=False),
                    tool_call_id=runtime.tool_call_id
                )]
            })

        attraction_names = list(coordinates.keys())

        # Separate attractions by classification type
        isolated_attractions = {}  # {name: day}
        preference_attractions = {}  # {name: day}
        flexible_attractions = []

        for name, info in classifications.items():
            if info["type"] == "isolated":
                isolated_attractions[name] = info["day"]
            elif info["type"] == "preference":
                preference_attractions[name] = info["day"]
            else:  # flexible
                flexible_attractions.append(name)

        LOGGER.info(f"Finalizing: {len(isolated_attractions)} isolated, {len(preference_attractions)} preference, {len(flexible_attractions)} flexible")

        # Get optimization config
        optimize_by_distance = optimization_config.get("enabled", False)
        starting_points = optimization_config.get("starting_points", {})
        ending_points = optimization_config.get("ending_points", {})

        # Days reserved for isolated attractions
        reserved_days = set(isolated_attractions.values())

        # Days available for K-means (not reserved)
        days_for_kmeans = [d for d in range(1, num_days + 1) if d not in reserved_days]

        # Build clusters array
        clusters = np.zeros(len(attraction_names), dtype=int)

        # Assign isolated attractions
        for name, day in isolated_attractions.items():
            if name in attraction_names:
                idx = attraction_names.index(name)
                clusters[idx] = day - 1

        # Assign preference attractions
        for name, day in preference_attractions.items():
            if name in attraction_names:
                idx = attraction_names.index(name)
                clusters[idx] = day - 1

        # SCENARIO 1: No flexible attractions - all predefined
        if len(flexible_attractions) == 0:
            LOGGER.info("Scenario: All attractions have defined days (no K-means)")

            # Group by day
            result_by_day_unordered = {}
            all_defined = {**isolated_attractions, **preference_attractions}
            for name in all_defined.keys():
                day = all_defined[name]
                result_by_day_unordered.setdefault(f"day_{day}", []).append(name)

            # Optionally optimize order
            if optimize_by_distance:
                result_by_day = {}
                for day_key, attractions in result_by_day_unordered.items():
                    day_num = int(day_key.split("_")[1])
                    day_label = f"Day {day_num}"

                    day_starting = starting_points.get(day_label)
                    day_ending = ending_points.get(day_label)

                    if day_starting and day_starting not in attractions:
                        LOGGER.warning(f"Starting point '{day_starting}' not in {day_label}, ignoring")
                        day_starting = None
                    if day_ending and day_ending not in attractions:
                        LOGGER.warning(f"Ending point '{day_ending}' not in {day_label}, ignoring")
                        day_ending = None

                    result_by_day[day_key] = _order_attractions_nearest_neighbor(
                        coordinates, attractions, day_starting, day_ending
                    )
                mode_message = "All attractions predefined. Order optimized by distance."
            else:
                result_by_day = result_by_day_unordered
                mode_message = "All attractions predefined. User order maintained."

            return Command(update={
                "clusters": clusters,
                "organized_days": result_by_day,
                "has_flexible_attractions": False,
                "messages": [ToolMessage(
                    json.dumps({
                        "mode": "predefined",
                        "optimized_by_distance": optimize_by_distance,
                        "message": mode_message,
                        "days": result_by_day
                    }, ensure_ascii=False, indent=2),
                    tool_call_id=runtime.tool_call_id
                )]
            })

        # SCENARIO 2: K-means for flexible attractions
        LOGGER.info(f"Scenario: K-means for {len(flexible_attractions)} flexible attractions")

        # Days with preferences (can add more) + free days, excluding exclusive days
        exclusive_days = set(runtime.state.get("exclusive_days", []))
        days_with_pref = set(preference_attractions.values())
        free_days = [d for d in days_for_kmeans if d not in days_with_pref]
        days_for_flex = [d for d in (list(days_with_pref) + free_days) if d not in exclusive_days]

        if not days_for_flex and flexible_attractions:
            return Command(update={
                "messages": [ToolMessage(
                    json.dumps({"error": "No days available for flexible attractions."}),
                    tool_call_id=runtime.tool_call_id
                )]
            })

        # Run K-means (with optional day constraints)
        coords_flex = np.array([[coordinates[n]["lat"], coordinates[n]["lon"]] for n in flexible_attractions])
        n_clusters_flex = min(len(days_for_flex), len(flexible_attractions))

        if n_clusters_flex > 0:
            constraints = runtime.state.get("day_constraints_config", {})
            min_per_day = constraints.get("min_per_day")
            max_per_day = constraints.get("max_per_day")
            use_constrained = min_per_day is not None or max_per_day is not None

            if use_constrained:
                size_min = min_per_day or 0
                size_max = max_per_day or len(flexible_attractions)

                # Feasibility check: total attractions must fit within constraints
                total_flex = len(flexible_attractions)
                if size_min * n_clusters_flex > total_flex:
                    return Command(update={
                        "messages": [ToolMessage(
                            json.dumps({
                                "error": f"Infeasible constraints: min_per_day={size_min} × {n_clusters_flex} clusters = {size_min * n_clusters_flex}, "
                                         f"but only {total_flex} flexible attractions available. Reduce min_per_day or add more attractions."
                            }, ensure_ascii=False),
                            tool_call_id=runtime.tool_call_id
                        )]
                    })
                if size_max * n_clusters_flex < total_flex:
                    return Command(update={
                        "messages": [ToolMessage(
                            json.dumps({
                                "error": f"Infeasible constraints: max_per_day={size_max} × {n_clusters_flex} clusters = {size_max * n_clusters_flex}, "
                                         f"but {total_flex} flexible attractions need placement. Increase max_per_day or reduce attractions."
                            }, ensure_ascii=False),
                            tool_call_id=runtime.tool_call_id
                        )]
                    })

                kmeans = KMeansConstrained(
                    n_clusters=n_clusters_flex,
                    size_min=size_min,
                    size_max=size_max,
                    random_state=42,
                )
                LOGGER.info(f"Using KMeansConstrained: size_min={size_min}, size_max={size_max}")
            else:
                kmeans = KMeans(n_clusters=n_clusters_flex, random_state=42, n_init=10)

            clusters_flex = kmeans.fit_predict(coords_flex)

            # Map clusters to days (prioritize days with preferences for proximity)
            cluster_to_day = {}

            if preference_attractions:
                pref_centroids = {}
                # Only compute centroids for preference days that are available for flex
                # (exclude exclusive days so clusters won't be matched to them)
                pref_days_for_flex = [d for d in days_with_pref if d not in exclusive_days]
                for day in pref_days_for_flex:
                    attractions_on_day = [n for n, d in preference_attractions.items() if d == day]
                    centroid = _calculate_centroid(coordinates, attractions_on_day)
                    if centroid:
                        pref_centroids[day] = centroid

                kmeans_centers = {i: (kmeans.cluster_centers_[i][0], kmeans.cluster_centers_[i][1])
                                  for i in range(n_clusters_flex)}

                assigned_clusters = set()
                assigned_days = set()

                # Match clusters to preference days by proximity
                for day, pref_center in pref_centroids.items():
                    best_cluster = None
                    best_dist = float('inf')
                    for cid, center in kmeans_centers.items():
                        if cid not in assigned_clusters:
                            dist = geodesic(pref_center, center).km
                            if dist < best_dist:
                                best_dist = dist
                                best_cluster = cid
                    if best_cluster is not None:
                        cluster_to_day[best_cluster] = day
                        assigned_clusters.add(best_cluster)
                        assigned_days.add(day)

                # Assign remaining clusters to free days
                for cid in range(n_clusters_flex):
                    if cid not in assigned_clusters:
                        for day in free_days:
                            if day not in assigned_days:
                                cluster_to_day[cid] = day
                                assigned_days.add(day)
                                break
                        else:
                            for day in days_for_flex:
                                if day not in assigned_days:
                                    cluster_to_day[cid] = day
                                    assigned_days.add(day)
                                    break
            else:
                for i, day in enumerate(days_for_flex[:n_clusters_flex]):
                    cluster_to_day[i] = day

            # Assign flexible attractions based on K-means
            for flex_idx, name in enumerate(flexible_attractions):
                cid = clusters_flex[flex_idx]
                day = cluster_to_day.get(cid, days_for_flex[0] if days_for_flex else 1)
                name_idx = attraction_names.index(name)
                clusters[name_idx] = day - 1

        # Build result grouped by day
        result_by_day_unordered = {}
        for idx, name in enumerate(attraction_names):
            day = clusters[idx] + 1
            result_by_day_unordered.setdefault(f"day_{day}", []).append(name)

        # Order attractions within each day
        result_by_day = {}
        for day_key, attractions in result_by_day_unordered.items():
            day_num = int(day_key.split("_")[1])
            day_label = f"Day {day_num}"

            day_starting = starting_points.get(day_label)
            day_ending = ending_points.get(day_label)

            if day_starting and day_starting not in attractions:
                LOGGER.warning(f"Starting point '{day_starting}' not in {day_label}, ignoring")
                day_starting = None
            if day_ending and day_ending not in attractions:
                LOGGER.warning(f"Ending point '{day_ending}' not in {day_label}, ignoring")
                day_ending = None

            result_by_day[day_key] = _order_attractions_nearest_neighbor(
                coordinates, attractions, day_starting, day_ending
            )

        message = "Flexible attractions grouped by geographic proximity (K-means)."

        return Command(update={
            "clusters": clusters,
            "organized_days": result_by_day,
            "has_flexible_attractions": True,
            "messages": [ToolMessage(
                json.dumps({
                    "mode": "kmeans" if not preference_attractions and not isolated_attractions else "mixed",
                    "message": message,
                    "isolated_days": list(reserved_days) if reserved_days else None,
                    "days": result_by_day
                }, ensure_ascii=False, indent=2),
                tool_call_id=runtime.tool_call_id
            )]
        })

    except Exception as e:
        LOGGER.error(f"Error in finalize_day_organization: {e}", exc_info=True)
        return Command(update={
            "messages": [ToolMessage(
                json.dumps({"error": f"Error: {str(e)}"}, ensure_ascii=False),
                tool_call_id=runtime.tool_call_id
            )]
        })


@tool
def organize_attractions_by_days(
    runtime: ToolRuntime,
    thinking: str = None,
    day_preferences: dict[str, int] = None,
    isolated_days: dict[str, int] = None,
    optimize_order_by_distance: bool = False,
    starting_points: dict[str, str] = None,
    ending_points: dict[str, str] = None,
    min_attractions_per_day: int = None,
    max_attractions_per_day: int = None,
) -> Command:
    """
    Organize attractions by days intelligently.

    This tool adapts automatically to the scenario based on the provided parameters.

    IMPORTANT: All coordinates must have been obtained via 'extract_coordinates' first.

    Args:
        thinking: MANDATORY. Your DETAILED reasoning explaining:
                  1) How you interpreted the user input (day labels, isolation requests, etc.)
                  2) Classification of each attraction (day_preferences vs isolated_days vs flexible)
                  3) WHICH PARAMETERS you will fill and WHY
                  4) The actual VALUES for each parameter
                  Format: "[Input analysis]. Therefore: day_preferences={...}, isolated_days={...},
                  optimize_order_by_distance=True/False, starting_point=..., min/max_attractions_per_day=..."

        day_preferences: Dict with {attraction_name: day_number} for attractions that
                         MUST be on a specific day. The preference is ABSOLUTE - the attraction
                         goes to the specified day regardless of K-means.
                         Other flexible attractions can be added to the same day.
                         Example: {"Eiffel Tower, Paris": 1} - Eiffel Tower on day 1.

        isolated_days: Dict with {attraction_name: day_number} for attractions that
                       need an EXCLUSIVE day for themselves (no other attractions).
                       Example: {"Disneyland Paris": 1} - Day 1 is only for Disneyland,
                       K-means groups the others on remaining days.

        optimize_order_by_distance: If True, optimize the order of attractions within each day
                                    by geographic proximity (nearest-neighbor algorithm).
                                    Useful when user specifies all days but wants distance optimization.
                                    Default: False (preserve user's order when all days are predefined).

        starting_points: Dict with {"Day 1": "attraction_name", "Day 2": "attraction_name"} specifying
                         where to start each day's route when optimizing by distance.
                         Only used when optimize_order_by_distance=True.
                         If attraction is not in that day's list, it's ignored for that day.
                         Example: {"Day 1": "Colosseum, Rome", "Day 2": "Vatican Museums"}

        ending_points: Dict with {"Day 1": "attraction_name", "Day 2": "attraction_name"} specifying
                       where to end each day's route when optimizing by distance.
                       Only used when optimize_order_by_distance=True.
                       If attraction is not in that day's list, it's ignored for that day.
                       Example: {"Day 1": "Roman Forum", "Day 2": "Castel Sant'Angelo"}

        min_attractions_per_day: Minimum number of attractions per day (for flexible attractions).
                                 Uses constrained K-means to ensure each cluster has at least this many members.
                                 The number of days/clusters remains unchanged.
                                 Example: min_attractions_per_day=2 ensures no day has fewer than 2 attractions.
                                 Note: Only applies to flexible attractions, not isolated days or preferences.

        max_attractions_per_day: Maximum number of attractions per day (for flexible attractions).
                                 Uses constrained K-means to ensure each cluster has at most this many members.
                                 The number of days/clusters remains unchanged.
                                 Example: max_attractions_per_day=4 ensures no day has more than 4 attractions.
                                 Note: Only applies to flexible attractions, not isolated days or preferences.

    Returns:
        Command that updates state with clusters and organization info.
    """
    try:
        # Validate thinking parameter is provided
        if not thinking or not thinking.strip():
            return Command(update={
                "messages": [ToolMessage(
                    json.dumps({
                        "error": "THINKING REQUIRED: You must fill the 'thinking' parameter with DETAILED reasoning: "
                                 "1) How you interpreted the user input (day labels, isolation requests, etc.), "
                                 "2) Classification of each attraction (day_preferences vs isolated_days vs flexible), "
                                 "3) WHICH PARAMETERS you will fill (day_preferences, isolated_days, optimize_order_by_distance, starting_point, min/max_attractions_per_day), "
                                 "4) The actual VALUES for each parameter. "
                                 "Example: 'User used dia 1:, dia 2: labels. ALL attractions have predefined days. "
                                 "Therefore: day_preferences={coliseu: 1, forum: 1, ...}, isolated_days={}, optimize_order_by_distance=False.'"
                    }, ensure_ascii=False),
                    tool_call_id=runtime.tool_call_id
                )]
            })

        LOGGER.info(f"Agent thinking: {thinking[:500]}...")

        # Check if itinerary was already approved - cannot reorganize after approval
        if runtime.state.get("itinerary_approved", False):
            return Command(update={
                "messages": [ToolMessage(
                    json.dumps({
                        "error": "CANNOT REORGANIZE: The itinerary has already been approved. "
                                 "To make changes, use 'update_itinerary_organization' tool instead."
                    }, ensure_ascii=False),
                    tool_call_id=runtime.tool_call_id
                )]
            })

        num_days = runtime.state.get("num_days")
        coordinates = runtime.state.get("attraction_coordinates", {})
        failed_lookups = runtime.state.get("failed_coordinate_lookups", [])

        # Filter out failures that were corrected by retry (attraction now has coordinates)
        unresolved_failures = [name for name in failed_lookups if name not in coordinates]

        if unresolved_failures:
            return Command(update={
                "messages": [ToolMessage(
                    json.dumps({
                        "error": f"Failed to get coordinates for: {unresolved_failures}. "
                                 f"Retry search_place_address with different queries for these attractions."
                    }, ensure_ascii=False),
                    tool_call_id=runtime.tool_call_id
                )]
            })

        if not coordinates:
            return Command(update={
                "messages": [ToolMessage(
                    json.dumps({"error": "No coordinates found. Call search_place_address for each attraction first."}, ensure_ascii=False),
                    tool_call_id=runtime.tool_call_id
                )]
            })

        attraction_names = list(coordinates.keys())
        prefs = day_preferences or {}
        isolated = isolated_days or {}

        # Validate day numbers are integers and within range [1, num_days]
        valid, error_msg = _validate_day_assignments(prefs, num_days, "day_preferences")
        if not valid:
            return Command(update={
                "messages": [ToolMessage(
                    json.dumps({"error": error_msg}, ensure_ascii=False),
                    tool_call_id=runtime.tool_call_id
                )]
            })

        valid, error_msg = _validate_day_assignments(isolated, num_days, "isolated_days")
        if not valid:
            return Command(update={
                "messages": [ToolMessage(
                    json.dumps({"error": error_msg}, ensure_ascii=False),
                    tool_call_id=runtime.tool_call_id
                )]
            })

        # Validate min/max attractions per day
        if min_attractions_per_day is not None and min_attractions_per_day < 1:
            return Command(update={
                "messages": [ToolMessage(
                    json.dumps({"error": "min_attractions_per_day must be >= 1"}, ensure_ascii=False),
                    tool_call_id=runtime.tool_call_id
                )]
            })

        if max_attractions_per_day is not None and max_attractions_per_day < 1:
            return Command(update={
                "messages": [ToolMessage(
                    json.dumps({"error": "max_attractions_per_day must be >= 1"}, ensure_ascii=False),
                    tool_call_id=runtime.tool_call_id
                )]
            })

        if (min_attractions_per_day is not None and max_attractions_per_day is not None
                and min_attractions_per_day > max_attractions_per_day):
            return Command(update={
                "messages": [ToolMessage(
                    json.dumps({
                        "error": f"min_attractions_per_day ({min_attractions_per_day}) cannot be greater than max_attractions_per_day ({max_attractions_per_day})"
                    }, ensure_ascii=False),
                    tool_call_id=runtime.tool_call_id
                )]
            })

        # Validate attractions have coordinates
        all_defined = {**prefs, **isolated}
        attractions_without_coords = [n for n in all_defined.keys() if n not in coordinates]
        if attractions_without_coords:
            return Command(update={
                "messages": [ToolMessage(
                    json.dumps({"error": f"Attractions without coordinates: {attractions_without_coords}. Check the names."}, ensure_ascii=False),
                    tool_call_id=runtime.tool_call_id
                )]
            })

        # Identify attraction groups (isolated takes precedence over prefs)
        isolated_attractions = {n: d for n, d in isolated.items() if n in coordinates}
        attractions_with_pref = {n: d for n, d in prefs.items() if n in coordinates and n not in isolated_attractions}
        flexible_attractions = [n for n in attraction_names if n not in isolated_attractions and n not in attractions_with_pref]

        LOGGER.info(f"Organizing: {len(isolated_attractions)} isolated, {len(attractions_with_pref)} with preference, {len(flexible_attractions)} flexible, {num_days} days")

        # Days reserved for isolated attractions (no other attractions allowed)
        reserved_days = set(isolated_attractions.values())

        # Validate preferences don't target reserved days
        prefs_on_reserved_days = {n: d for n, d in attractions_with_pref.items() if d in reserved_days}
        if prefs_on_reserved_days:
            return Command(update={
                "messages": [ToolMessage(
                    json.dumps({
                        "error": f"Conflict: preferences point to isolated days. "
                                 f"Attractions {list(prefs_on_reserved_days.keys())} want days {list(prefs_on_reserved_days.values())} "
                                 f"but those days are reserved for isolated attractions."
                    }, ensure_ascii=False),
                    tool_call_id=runtime.tool_call_id
                )]
            })

        days_for_kmeans = [d for d in range(1, num_days + 1) if d not in reserved_days]

        # SCENARIO 1: All attractions have assigned days (all in prefs or isolated)
        if len(flexible_attractions) == 0:
            LOGGER.info(f"Scenario: All attractions have defined days (optimize_order_by_distance={optimize_order_by_distance})")
            # IMPORTANT: clusters must be aligned with attraction_names order (from coordinates.keys())
            # because the map visualization uses coordinates.keys() to iterate
            clusters = np.array([all_defined.get(n, 1) - 1 for n in attraction_names])

            # Group by day - preserve user's order from preferences (all_defined.keys())
            result_by_day_unordered = {}
            for n in all_defined.keys():
                day = all_defined.get(n, 1)
                result_by_day_unordered.setdefault(f"day_{day}", []).append(n)

            # Optionally optimize order within each day by distance
            if optimize_order_by_distance:
                result_by_day = {}
                for day_key, attractions in result_by_day_unordered.items():
                    # Extract day number from day_key (e.g., "day_1" -> 1)
                    day_num = int(day_key.split("_")[1])
                    day_label = f"Day {day_num}"

                    # Get per-day starting and ending points
                    day_starting = starting_points.get(day_label) if starting_points else None
                    day_ending = ending_points.get(day_label) if ending_points else None

                    # Only use if attraction is in this day's list
                    if day_starting and day_starting not in attractions:
                        LOGGER.warning(f"Starting point '{day_starting}' not in {day_label} attractions, ignoring")
                        day_starting = None
                    if day_ending and day_ending not in attractions:
                        LOGGER.warning(f"Ending point '{day_ending}' not in {day_label} attractions, ignoring")
                        day_ending = None

                    result_by_day[day_key] = _order_attractions_nearest_neighbor(
                        coordinates, attractions, day_starting, day_ending
                    )
                mode_message = "Days predefined by user, order optimized by distance within each day."
                if starting_points:
                    mode_message += f" Starting points: {starting_points}."
                if ending_points:
                    mode_message += f" Ending points: {ending_points}."
            else:
                result_by_day = result_by_day_unordered
                mode_message = "User organization maintained."

            return Command(update={
                "clusters": clusters,
                "organized_days": result_by_day,
                "has_flexible_attractions": False,  # All predefined, no approval needed
                "messages": [ToolMessage(
                    json.dumps({
                        "mode": "predefined",
                        "optimized_by_distance": optimize_order_by_distance,
                        "starting_points": starting_points,
                        "ending_points": ending_points,
                        "message": mode_message,
                        "days": result_by_day
                    }, ensure_ascii=False, indent=2),
                    tool_call_id=runtime.tool_call_id
                )]
            })

        # SCENARIO 2: K-means clustering for flexible attractions only
        # Preferences are ABSOLUTE - they go directly to their day, not through K-means
        LOGGER.info(f"K-means on {len(flexible_attractions)} flexible attractions for {len(days_for_kmeans)} days")

        # Check if we have days available for flexible attractions
        # Days used by preferences (but not exclusive, so K-means can add more)
        days_with_pref = set(attractions_with_pref.values())
        # Days that are truly free (no isolated, no pref)
        free_days = [d for d in days_for_kmeans if d not in days_with_pref]

        # Total "slots" for K-means = days with prefs (can add more) + free days
        days_for_flex = list(days_with_pref) + free_days

        if not days_for_flex and flexible_attractions:
            return Command(update={
                "messages": [ToolMessage(
                    json.dumps({"error": "No days available to group flexible attractions."}, ensure_ascii=False),
                    tool_call_id=runtime.tool_call_id
                )]
            })

        # Build final clusters array
        clusters = np.zeros(len(attraction_names), dtype=int)

        # First, assign isolated attractions to their exclusive days
        for idx, name in enumerate(attraction_names):
            if name in isolated_attractions:
                clusters[idx] = isolated_attractions[name] - 1

        # Second, assign attractions with preferences to their preferred days (ABSOLUTE)
        for idx, name in enumerate(attraction_names):
            if name in attractions_with_pref:
                clusters[idx] = attractions_with_pref[name] - 1

        # Third, K-means for flexible attractions
        if flexible_attractions:
            coords_flex = np.array([[coordinates[n]["lat"], coordinates[n]["lon"]] for n in flexible_attractions])
            n_clusters_flex = min(len(days_for_flex), len(flexible_attractions))

            if n_clusters_flex > 0:
                # Use constrained K-means if min/max constraints are provided
                use_constrained = min_attractions_per_day is not None or max_attractions_per_day is not None

                if use_constrained:
                    # Calculate size constraints
                    size_min = min_attractions_per_day if min_attractions_per_day else 0
                    size_max = max_attractions_per_day if max_attractions_per_day else len(flexible_attractions)

                    # Validate constraints are feasible
                    total_attractions = len(flexible_attractions)
                    min_possible = size_min * n_clusters_flex
                    max_possible = size_max * n_clusters_flex

                    if min_possible > total_attractions:
                        return Command(update={
                            "messages": [ToolMessage(
                                json.dumps({
                                    "error": f"Impossible constraint: min_attractions_per_day={size_min} with {n_clusters_flex} days requires at least {min_possible} attractions, but only {total_attractions} are available."
                                }, ensure_ascii=False),
                                tool_call_id=runtime.tool_call_id
                            )]
                        })

                    if max_possible < total_attractions:
                        return Command(update={
                            "messages": [ToolMessage(
                                json.dumps({
                                    "error": f"Impossible constraint: max_attractions_per_day={size_max} with {n_clusters_flex} days can only fit {max_possible} attractions, but {total_attractions} need to be assigned."
                                }, ensure_ascii=False),
                                tool_call_id=runtime.tool_call_id
                            )]
                        })

                    LOGGER.info(f"Using constrained K-means: size_min={size_min}, size_max={size_max}")
                    kmeans = KMeansConstrained(
                        n_clusters=n_clusters_flex,
                        size_min=size_min,
                        size_max=size_max,
                        random_state=42
                    )
                else:
                    kmeans = KMeans(n_clusters=n_clusters_flex, random_state=42, n_init=10)

                clusters_flex = kmeans.fit_predict(coords_flex)

                # Map K-means clusters to available days
                # Prioritize days that already have preferences (to group nearby attractions)
                cluster_to_day = {}

                if attractions_with_pref:
                    # Calculate centroid of each preference day
                    pref_centroids = {}
                    for day in days_with_pref:
                        attractions_on_day = [n for n, d in attractions_with_pref.items() if d == day]
                        centroid = _calculate_centroid(coordinates, attractions_on_day)
                        if centroid:
                            pref_centroids[day] = centroid

                    # Calculate K-means cluster centers
                    kmeans_centers = {i: (kmeans.cluster_centers_[i][0], kmeans.cluster_centers_[i][1])
                                      for i in range(n_clusters_flex)}

                    # Greedy assignment: match clusters to nearest preference day or free day
                    assigned_clusters = set()
                    assigned_days = set()

                    # First pass: assign clusters to preference days by proximity
                    for day, pref_center in pref_centroids.items():
                        best_cluster = None
                        best_dist = float('inf')
                        for cid, center in kmeans_centers.items():
                            if cid not in assigned_clusters:
                                dist = geodesic(pref_center, center).km
                                if dist < best_dist:
                                    best_dist = dist
                                    best_cluster = cid
                        if best_cluster is not None:
                            cluster_to_day[best_cluster] = day
                            assigned_clusters.add(best_cluster)
                            assigned_days.add(day)

                    # Second pass: assign remaining clusters to free days
                    for cid in range(n_clusters_flex):
                        if cid not in assigned_clusters:
                            for day in free_days:
                                if day not in assigned_days:
                                    cluster_to_day[cid] = day
                                    assigned_days.add(day)
                                    break
                            else:
                                # Fallback: use any available day from days_for_flex
                                for day in days_for_flex:
                                    if day not in assigned_days:
                                        cluster_to_day[cid] = day
                                        assigned_days.add(day)
                                        break
                else:
                    # No preferences, just map clusters to available days
                    for i, day in enumerate(days_for_flex[:n_clusters_flex]):
                        cluster_to_day[i] = day

                # Assign flexible attractions based on K-means results
                for flex_idx, name in enumerate(flexible_attractions):
                    cid = clusters_flex[flex_idx]
                    day = cluster_to_day.get(cid, days_for_flex[0] if days_for_flex else 1)
                    name_idx = attraction_names.index(name)
                    clusters[name_idx] = day - 1

        # Build result grouped by day (unordered first)
        result_by_day_unordered = {}
        for idx, name in enumerate(attraction_names):
            day = clusters[idx] + 1
            result_by_day_unordered.setdefault(f"day_{day}", []).append(name)

        # Order attractions within each day using nearest-neighbor from center
        result_by_day = {}
        for day_key, attractions in result_by_day_unordered.items():
            # Extract day number from day_key (e.g., "day_1" -> 1)
            day_num = int(day_key.split("_")[1])
            day_label = f"Day {day_num}"

            # Get per-day starting and ending points
            day_starting = starting_points.get(day_label) if starting_points else None
            day_ending = ending_points.get(day_label) if ending_points else None

            # Only use if attraction is in this day's list
            if day_starting and day_starting not in attractions:
                LOGGER.warning(f"Starting point '{day_starting}' not in {day_label} attractions, ignoring")
                day_starting = None
            if day_ending and day_ending not in attractions:
                LOGGER.warning(f"Ending point '{day_ending}' not in {day_label} attractions, ignoring")
                day_ending = None

            result_by_day[day_key] = _order_attractions_nearest_neighbor(
                coordinates, attractions, day_starting, day_ending
            )

        message = "Attractions organized by geographic proximity. The order within each day is already optimized to minimize travel."
        if starting_points:
            message += f" Starting points: {starting_points}."
        if ending_points:
            message += f" Ending points: {ending_points}."
        if min_attractions_per_day:
            message += f" Minimum {min_attractions_per_day} attractions per day enforced."
        if max_attractions_per_day:
            message += f" Maximum {max_attractions_per_day} attractions per day enforced."

        return Command(update={
            "clusters": clusters,
            "organized_days": result_by_day,
            "has_flexible_attractions": True,  # K-means was used, approval needed
            "messages": [ToolMessage(
                json.dumps({
                    "mode": "kmeans" if not isolated_attractions and not attractions_with_pref else "mixed",
                    "message": message,
                    "isolated_days": list(reserved_days) if reserved_days else None,
                    "starting_points": starting_points,
                    "ending_points": ending_points,
                    "min_attractions_per_day": min_attractions_per_day,
                    "max_attractions_per_day": max_attractions_per_day,
                    "days": result_by_day,
                }, ensure_ascii=False, indent=2),
                tool_call_id=runtime.tool_call_id
            )]
        })

    except Exception as e:
        LOGGER.error(f"Error organizing attractions: {e}", exc_info=True)
        return Command(update={
            "messages": [ToolMessage(
                json.dumps({"error": f"Error: {str(e)}"}, ensure_ascii=False),
                tool_call_id=runtime.tool_call_id
            )]
        })


@tool
def return_invalid_input_error(
    message: str,
    runtime: ToolRuntime,
) -> Command:
    """
    Use this tool when user input is INVALID or UNRELATED.

    Use cases:
    1. EMPTY INPUT: User didn't provide any attractions
    2. UNRELATED QUESTION: User asked something not about organizing itineraries
       (e.g., "What is the Eiffel Tower?", "Tell me about Paris")
    3. INPUT WITHOUT ATTRACTIONS: User wrote something but didn't mention tourist attractions

    IMPORTANT: This tool ENDS the flow. Use only when there's no way to proceed.

    Args:
        message: Explanatory message for the user about why the input is invalid
                 and what they should provide (polite and clear)

    Returns:
        Command that updates state with invalid_input=True and error_message
    """
    LOGGER.warning(f"Invalid input detected: {message}")

    return Command(update={
        "invalid_input": True,
        "error_message": message,
        "messages": [ToolMessage(
            json.dumps({
                "status": "invalid_input",
                "message": message
            }, ensure_ascii=False, indent=2),
            tool_call_id=runtime.tool_call_id
        )]
    })


@tool
def request_itinerary_approval(
    runtime: ToolRuntime,
) -> Command:
    """
    Request user approval for the organized itinerary BEFORE generating the document.

    IMPORTANT: Use this tool ONLY when has_flexible_attractions=True in the state.
    The tool reads the organized_days directly from the state (set by organize_attractions_by_days).
    Do NOT use when ALL attractions have predefined days.

    This tool pauses execution and asks the user to review the proposed day organization.
    The user can either approve or request changes.

    Args:
        None - reads organized_days from state automatically.

    Returns:
        Command with user's response:
        - If approved: {"approved": True}
        - If changes requested: {"approved": False, "feedback": "user's feedback"}
          In this case, use update_itinerary_organization to apply changes, then call this tool again.
    """
    # Read organized_days from state
    organized_days = runtime.state.get("organized_days", {})

    if not organized_days:
        return Command(update={
            "messages": [ToolMessage(
                json.dumps({
                    "error": "No organized_days found in state. Call organize_attractions_by_days first."
                }, ensure_ascii=False),
                tool_call_id=runtime.tool_call_id
            )]
        })

    LOGGER.info("Requesting user approval for itinerary organization")

    # Format the itinerary for display
    itinerary_display = []
    for day_key in sorted(organized_days.keys(), key=lambda x: int(x.split("_")[1])):
        day_num = day_key.split("_")[1]
        attractions = organized_days[day_key]
        itinerary_display.append({
            "day": int(day_num),
            "attractions": attractions
        })

    # Use interrupt to pause and get user approval
    user_response = interrupt({
        "type": "itinerary_approval",
        "itinerary": itinerary_display,
    })

    # Process user response
    # user_response is expected to be a string: "yes"/"ok"/"approved" or feedback text
    response_lower = str(user_response).lower().strip()
    is_approved = response_lower in ["yes", "ok", "okay", "approved", "approve", "sim", "si", "oui", "y"]

    if is_approved:
        LOGGER.info("User approved the itinerary organization")
        return Command(update={
            "itinerary_approved": True,
            "messages": [ToolMessage(
                json.dumps({
                    "approved": True,
                    "message": "User approved the itinerary. Proceed with document generation."
                }, ensure_ascii=False, indent=2),
                tool_call_id=runtime.tool_call_id
            )]
        })
    else:
        LOGGER.info(f"User requested changes: {user_response}")
        return Command(update={
            "itinerary_approved": False,
            "user_feedback": str(user_response),
            "messages": [ToolMessage(
                json.dumps({
                    "approved": False,
                    "feedback": str(user_response),
                }, ensure_ascii=False, indent=2),
                tool_call_id=runtime.tool_call_id
            )]
        })


@tool
def update_itinerary_organization(
    new_organized_days: dict[str, list[str]],
    runtime: ToolRuntime,
) -> Command:
    """
    Manually update the itinerary organization based on user feedback.

    Use this tool AFTER request_itinerary_approval returns approved=False.
    This tool updates both organized_days and clusters in the state.

    Args:
        new_organized_days: The new organization after applying user's feedback.
                            Format: {"day_1": ["Attraction A", "Attraction B"], "day_2": [...]}
                            Must include ALL attractions from the original organization.

    Returns:
        Command that updates state with the new organization and recalculated clusters.
    """
    coordinates = runtime.state.get("attraction_coordinates", {})
    attraction_names = list(coordinates.keys())

    if not coordinates:
        return Command(update={
            "messages": [ToolMessage(
                json.dumps({"error": "No coordinates found in state."}, ensure_ascii=False),
                tool_call_id=runtime.tool_call_id
            )]
        })

    # Validate all attractions are included
    all_attractions_in_new = set()
    for day_key, attractions in new_organized_days.items():
        all_attractions_in_new.update(attractions)

    missing_attractions = set(attraction_names) - all_attractions_in_new
    if missing_attractions:
        return Command(update={
            "messages": [ToolMessage(
                json.dumps({
                    "error": f"Missing attractions in new organization: {list(missing_attractions)}"
                }, ensure_ascii=False),
                tool_call_id=runtime.tool_call_id
            )]
        })

    extra_attractions = all_attractions_in_new - set(attraction_names)
    if extra_attractions:
        return Command(update={
            "messages": [ToolMessage(
                json.dumps({
                    "error": f"Unknown attractions in new organization: {list(extra_attractions)}"
                }, ensure_ascii=False),
                tool_call_id=runtime.tool_call_id
            )]
        })

    # Recalculate clusters based on new organization
    clusters = np.zeros(len(attraction_names), dtype=int)
    for day_key, attractions in new_organized_days.items():
        day_num = int(day_key.split("_")[1]) - 1  # 0-indexed
        for attraction in attractions:
            if attraction in attraction_names:
                idx = attraction_names.index(attraction)
                clusters[idx] = day_num

    LOGGER.info(f"Updated itinerary organization: {new_organized_days}")

    return Command(update={
        "clusters": clusters,
        "organized_days": new_organized_days,
        "messages": [ToolMessage(
            json.dumps({
                "success": True,
                "message": "Itinerary organization updated. Call request_itinerary_approval to get user confirmation.",
                "days": new_organized_days
            }, ensure_ascii=False, indent=2),
            tool_call_id=runtime.tool_call_id
        )]
    })


# ============================================================================
# Tool Lists for Each Agent
# ============================================================================

# Coordinate finder agent - focused on finding coordinates for all attractions
COORDINATE_FINDER_TOOLS = [
    search_place_address,
    return_invalid_input_error,
]

# Day organizer agent - classification, optimization, finalization, approval
# 3-step workflow: classify_attractions → configure_route_optimization (optional) → finalize_day_organization
DAY_ORGANIZER_TOOLS = [
    classify_attractions,
    configure_route_optimization,
    configure_day_constraints,
    finalize_day_organization,
    request_itinerary_approval,
    update_itinerary_organization,
]

# Second agent (attraction researcher) - needs search, images, ticket search, and ticket validation
ATTRACTION_RESEARCHER_TOOLS = [
    search_attraction_info,
    search_attraction_images,
    search_ticket_link,
]
