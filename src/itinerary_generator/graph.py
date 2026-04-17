"""
LangGraph definition for the multi-agent itinerary generation system.

Graph flow:
  START → coordinate_finder_node → (invalid input?) → END
                                 → (valid input?) → day_organizer_node → [attraction_researcher_node (parallel)] → build_document_node → END

Features:
- Three specialized agents (coordinate finder, day organizer, and attraction researcher)
- Map-reduce pattern using Send API for parallel day research
- Structured outputs using TypedDict
- Multi-language support
- Early exit for invalid/unrelated input
"""
from langgraph.graph import StateGraph, END
from src.itinerary_generator.state import GraphState
from src.itinerary_generator.agent_definition import coordinate_finder_node, day_organizer_node, attraction_researcher_node
from src.itinerary_generator.other_nodes import check_invalid_input, assign_workers_node, build_document_node
from src.utils.logger import LOGGER


def build_graph(checkpointer=None) -> StateGraph:
    """
    Build and compile the multi-agent itinerary generation graph.

    Graph structure:
      START → coordinate_finder_node → (invalid?) → END
                                     → (valid?) → day_organizer_node → [attraction_researcher_node] → build_document_node → END

    Args:
        checkpointer: Optional checkpointer for state persistence and interrupt support

    Returns:
        Compiled StateGraph ready for execution
    """
    LOGGER.info("Building multi-agent itinerary generation graph...")

    # Create graph with state schema
    workflow = StateGraph(GraphState)

    # Add nodes
    workflow.add_node("coordinate_finder_node", coordinate_finder_node)
    workflow.add_node("day_organizer_node", day_organizer_node)
    workflow.add_node("attraction_researcher_node", attraction_researcher_node)
    workflow.add_node("build_document_node", build_document_node)

    # Set entry point
    workflow.set_entry_point("coordinate_finder_node")

    # coordinate_finder → check invalid → day_organizer or END
    workflow.add_conditional_edges(
        "coordinate_finder_node",
        check_invalid_input,
        ["day_organizer_node", END],
    )

    # day_organizer → assign_workers → researchers or END
    workflow.add_conditional_edges(
        "day_organizer_node",
        assign_workers_node,
        ["attraction_researcher_node", END],
    )

    # After all attraction_researcher_node calls complete, go to build_document_node
    workflow.add_edge("attraction_researcher_node", "build_document_node")

    # End after document is built
    workflow.add_edge("build_document_node", END)

    # Compile graph with optional checkpointer
    graph = workflow.compile(checkpointer=checkpointer)
    LOGGER.info("Graph compiled successfully")
    return graph
