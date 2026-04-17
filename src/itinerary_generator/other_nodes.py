"""
Helper nodes for the multi-agent itinerary generation graph.

Contains:
- check_invalid_input: Routes to END if input is invalid, otherwise to day_organizer_node
- assign_workers_node: Creates Send() calls to distribute work to attraction researcher agents
- build_document_node: Final node that generates the PDF document
"""
import os
from typing import Dict, Any, List, Union, Literal
from langgraph.types import Send
from langgraph.graph import END
from src.itinerary_generator.state import GraphState
from src.processor.pdf_processor import ItineraryPDFGenerator
from src.utils.utilities import plot_clusters_on_basemap
from src.utils.logger import LOGGER

_pdf_generator = None

def get_pdf_generator():
    """Get or create PDF generator."""
    global _pdf_generator
    if _pdf_generator is None:
        _pdf_generator = ItineraryPDFGenerator()
    return _pdf_generator


def check_invalid_input(state: GraphState):
    """
    Routing function that checks if input was marked as invalid by coordinate_finder_node.

    Returns END if invalid_input=True, otherwise routes to day_organizer_node.

    Args:
        state: Graph state with invalid_input flag

    Returns:
        END or "day_organizer_node"
    """
    if state.get("invalid_input", False):
        LOGGER.warning("Input marked as invalid by coordinate finder - routing to END")
        return END
    return "day_organizer_node"


def assign_workers_node(state: GraphState) -> Union[List[Send], Literal["__end__"]]:
    """
    Create Send() calls to assign each DAY to the researcher agent.

    This node implements the map-reduce pattern by:
    1. Taking the organized attractions by day from first agent
    2. Creating a Send() call for EACH DAY to the attraction_researcher_node
    3. Each Send() runs in parallel (one per day)

    If invalid_input is True, returns END to terminate the graph.

    Args:
        state: Graph state containing attractions_by_day from day organizer

    Returns:
        END if input is invalid, otherwise list of Send() calls
    """
    # Check if input was marked as invalid by the day organizer
    if state.get("invalid_input", False):
        LOGGER.warning("Input marked as invalid - routing to END")
        return END

    LOGGER.info("Assigning workers for attraction research...")

    attractions_by_day = state.get("attractions_by_day", [])
    preferences_input = state.get("preferences_input", "")
    language = state.get("language", "en")

    if not attractions_by_day:
        LOGGER.warning("No attractions found in state to assign")
        return []

    # Create Send() calls for each DAY (not each attraction)
    sends = []

    for day_data in attractions_by_day:
        day_number = day_data.get("day", 1)
        attractions = day_data.get("attractions", [])

        LOGGER.info(f"Creating worker for Day {day_number} with {len(attractions)} attractions")

        # Each Send() will invoke attraction_researcher_node with ALL attractions for this day
        sends.append(
            Send(
                "attraction_researcher_node",
                {
                    "attractions": attractions,  # List of all attraction names for this day
                    "day_number": day_number,
                    "preferences_input": preferences_input,
                    "language": language,
                    "attractions_by_day": state.get("attractions_by_day", {}),
                },
            )
        )

    LOGGER.info(f"Created {len(sends)} workers for parallel day research")
    return sends


def build_document_node(state: GraphState) -> Dict[str, Any]:
    """
    Build the final PDF document from all processed attractions.

    This node:
    1. Takes all processed_attractions from state (accumulated from parallel executions)
    2. Groups them by day
    3. Generates PDF document with proper structure and clickable links
    4. Calculates costs grouped by currency
    5. Returns final document path

    Note: This node is only called when input is valid (invalid input routes to END).

    Args:
        state: Graph state containing processed_attractions

    Returns:
        Updated state with final_document_path and costs_by_currency
    """
    LOGGER.info("Building final PDF document...")

    processed_attractions = state.get("processed_attractions", [])
    num_days = state.get("num_days", 3)
    document_title = state.get("document_title", f"Travel Itinerary - {num_days} Days")
    language = state.get("language", "en")

    if not processed_attractions:
        LOGGER.error("No processed attractions found in state")
        return {
            "final_document_path": "",
            "costs_by_currency": {},
        }

    LOGGER.info(f"Processing {len(processed_attractions)} attractions for PDF document")

    # Group attractions by day
    attractions_by_day: Dict[int, List[Dict[str, Any]]] = {}
    costs_by_currency: Dict[str, float] = {}

    for attraction in processed_attractions:
        if not isinstance(attraction, dict):
            LOGGER.warning(f"Attraction is not a dict: {type(attraction).__name__}")
            continue

        day_number = attraction.get("day_number", 1)
        if day_number not in attractions_by_day:
            attractions_by_day[day_number] = []
        attractions_by_day[day_number].append(attraction)

        # Accumulate costs by currency
        cost = attraction.get("estimated_cost", 0.0)
        currency = attraction.get("currency", "EUR")
        if cost > 0:
            if currency not in costs_by_currency:
                costs_by_currency[currency] = 0.0
            costs_by_currency[currency] += cost

    LOGGER.info(f"Grouped attractions into {len(attractions_by_day)} days")

    # Generate map image
    map_image_path = None
    attraction_coordinates = state.get("attraction_coordinates", {})
    clusters = state.get("clusters", [])
    organized_days_state = state.get("organized_days", {})
    attractions_by_day_state = state.get("attractions_by_day", [])

    # Prefer organized_days (tool-produced, distance-optimized order) over
    # attractions_by_day (LLM-produced, may be reordered)
    if organized_days_state:
        attractions_by_day_state = []
        for day_key in sorted(organized_days_state.keys(), key=lambda x: int(x.split("_")[1])):
            day_num = int(day_key.split("_")[1])
            attractions_by_day_state.append({"day": day_num, "attractions": organized_days_state[day_key]})

    if attraction_coordinates and hasattr(clusters, 'tolist'):
        try:
            # Build data in itinerary order (Day 1 attractions first, then Day 2, etc.)
            ordered_names = []
            ordered_locs = []
            ordered_clusters = []

            for day_data in attractions_by_day_state:
                day_num = day_data.get("day", 1)
                day_attractions = day_data.get("attractions", [])
                # Find clean titles from processed_attractions for this day
                same_day_processed = [p for p in processed_attractions
                                      if isinstance(p, dict) and p.get("day_number") == day_num]
                for pos, attr_name in enumerate(day_attractions):
                    if attr_name in attraction_coordinates:
                        coord = attraction_coordinates[attr_name]
                        ordered_locs.append((coord['lon'], coord['lat']))
                        ordered_clusters.append(day_num - 1)  # 0-indexed
                        # Use clean title if available
                        if pos < len(same_day_processed):
                            ordered_names.append(same_day_processed[pos].get("name", attr_name))
                        else:
                            ordered_names.append(attr_name)

            generator = get_pdf_generator()
            map_image_path = os.path.join(generator.output_dir, "route_map.png")

            plot_clusters_on_basemap(
                locations=ordered_locs,
                clusters=ordered_clusters,
                names=ordered_names,
                out_path=map_image_path,
                title=document_title
            )
            LOGGER.info(f"Route map generated: {map_image_path}")

        except Exception as e:
            LOGGER.error(f"Error generating route map: {e}", exc_info=True)
            map_image_path = None

    # Create PDF document
    try:
        generator = get_pdf_generator()
        LOGGER.info("PDF generator initialized")

        LOGGER.info(f"Using document title: {document_title}")
        LOGGER.info(f"Creating PDF with {sum(len(v) for v in attractions_by_day.values())} attractions (language: {language})")

        file_path = generator.create_document(
            title=document_title,
            attractions_by_day=attractions_by_day,
            costs_by_currency=costs_by_currency,
            map_image_path=map_image_path,
            language=language
        )

        LOGGER.info(f"PDF document created successfully at: {file_path}")

        # Clean up map image
        if map_image_path and os.path.exists(map_image_path):
            try:
                os.remove(map_image_path)
            except Exception:
                pass

        if not file_path or not os.path.exists(file_path):
            LOGGER.error(f"PDF file does not exist: {file_path}")
            return {
                "final_document_path": "",
                "costs_by_currency": costs_by_currency,
            }

        return {
            "final_document_path": file_path,
            "costs_by_currency": costs_by_currency,
        }

    except Exception as e:
        LOGGER.error(f"PDF generation failed: {e}", exc_info=True)
        return {
            "final_document_path": "",
            "costs_by_currency": costs_by_currency,
        }
