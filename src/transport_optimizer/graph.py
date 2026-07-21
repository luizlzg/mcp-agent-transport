"""LangGraph workflow definition for the transport optimizer."""
from typing import Literal, Union
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.utils.logger import LOGGER
from src.transport_optimizer.state import TransportOptimizerState
from src.transport_optimizer.agent_definition import (
    route_collector_node,
    transport_overview_node,
    transport_researcher_node,
    cost_calculator_node,
    pdf_generator_node,
)


def determine_entry_point(state: TransportOptimizerState) -> str:
    """Determine which agent should handle the input based on current state.

    This is used as a conditional entry point so the graph resumes at the
    correct agent after user provides input.

    Args:
        state: Current graph state

    Returns:
        Name of the agent to start with
    """
    # If interaction is complete, don't process
    if state.get("interaction_complete", False):
        LOGGER.info("Entry: interaction complete, going to END")
        return END

    # If next_agent is pdf_generator, go directly there
    next_agent = state.get("next_agent", "")
    if next_agent == "pdf_generator":
        LOGGER.info("Entry: next_agent is pdf_generator, starting at pdf_generator")
        return "pdf_generator"

    # If all preferences collected, go to cost calculator
    if state.get("all_preferences_collected", False):
        LOGGER.info("Entry: all preferences collected, starting at cost_calculator")
        return "cost_calculator"

    # If pairs confirmed but the general overview hasn't been researched, do that first
    if state.get("pairs_confirmed", False) and not state.get("transport_overview_complete", False):
        LOGGER.info("Entry: pairs confirmed, overview pending, starting at transport_overview")
        return "transport_overview"

    # If pairs confirmed (and overview done) but not all preferences, go to transport researcher
    if state.get("pairs_confirmed", False):
        LOGGER.info("Entry: pairs confirmed, starting at transport_researcher")
        return "transport_researcher"

    # Default: start with route collector
    LOGGER.info("Entry: starting at route_collector")
    return "route_collector"


def route_based_on_state(state: TransportOptimizerState) -> str:
    """Route to the next agent based on the next_agent state field.

    Each agent sets the next_agent field when it's done with its task.

    Args:
        state: Current graph state

    Returns:
        Name of the next node to execute, or END
    """
    next_agent = state.get("next_agent", "route_collector")

    LOGGER.info(f"Finishing interaction, routing decision: next_agent = {next_agent}")

    if next_agent == "end":
        return END
    elif next_agent in ["route_collector", "transport_overview", "transport_researcher", "cost_calculator", "pdf_generator"]:
        return next_agent
    else:
        # Default to route_collector if unknown
        LOGGER.warning(f"Unknown next_agent value: {next_agent}, defaulting to route_collector")
        return "route_collector"


def build_transport_optimizer_graph(checkpointer=None) -> StateGraph:
    """Build the transport optimizer multi-agent graph.

    Graph Structure:
    ```
                        START
                          │
                          ▼ (conditional entry based on state)
           ┌──────────────┼──────────────┐
           │              │              │
           ▼              ▼              ▼
    route_collector  transport_researcher  cost_calculator
           │              │              │
           └──────────────┴──────────────┘
                          │
                          ▼ (conditional routing)
                         END
    ```

    Entry point is determined by state:
    - pairs_confirmed=False → route_collector
    - pairs_confirmed=True, all_preferences_collected=False → transport_researcher
    - all_preferences_collected=True → cost_calculator

    Args:
        checkpointer: Optional checkpointer for state persistence

    Returns:
        Compiled StateGraph
    """
    LOGGER.info("Building transport optimizer multi-agent graph...")

    # Create the workflow graph
    workflow = StateGraph(TransportOptimizerState)

    # Add nodes for each agent
    workflow.add_node("route_collector", route_collector_node)
    workflow.add_node("transport_overview", transport_overview_node)
    workflow.add_node("transport_researcher", transport_researcher_node)
    workflow.add_node("cost_calculator", cost_calculator_node)
    workflow.add_node("pdf_generator", pdf_generator_node)

    # Set conditional entry point - determines which agent handles input based on state
    workflow.set_conditional_entry_point(
        determine_entry_point,
        {
            "route_collector": "route_collector",
            "transport_overview": "transport_overview",
            "transport_researcher": "transport_researcher",
            "cost_calculator": "cost_calculator",
            "pdf_generator": "pdf_generator",
            END: END,
        }
    )

    # Add conditional edges from each node
    # Each agent sets next_agent to determine where to go next

    # From route_collector: can stay (waiting for input), go to researcher, or end
    workflow.add_conditional_edges(
        "route_collector",
        route_based_on_state,
        {
            "route_collector": "route_collector",
            "transport_overview": "transport_overview",
            "transport_researcher": "transport_researcher",
            "cost_calculator": "cost_calculator",
            "pdf_generator": "pdf_generator",
            END: END,
        }
    )

    # From transport_overview: silent step, always continues to transport_researcher
    workflow.add_conditional_edges(
        "transport_overview",
        route_based_on_state,
        {
            "route_collector": "route_collector",
            "transport_overview": "transport_overview",
            "transport_researcher": "transport_researcher",
            "cost_calculator": "cost_calculator",
            "pdf_generator": "pdf_generator",
            END: END,
        }
    )

    # From transport_researcher: can stay (more pairs), go to calculator, or end
    workflow.add_conditional_edges(
        "transport_researcher",
        route_based_on_state,
        {
            "route_collector": "route_collector",
            "transport_overview": "transport_overview",
            "transport_researcher": "transport_researcher",
            "cost_calculator": "cost_calculator",
            "pdf_generator": "pdf_generator",
            END: END,
        }
    )

    # From cost_calculator: can stay (answering questions), go to pdf_generator, or end
    workflow.add_conditional_edges(
        "cost_calculator",
        route_based_on_state,
        {
            "route_collector": "route_collector",
            "transport_overview": "transport_overview",
            "transport_researcher": "transport_researcher",
            "cost_calculator": "cost_calculator",
            "pdf_generator": "pdf_generator",
            END: END,
        }
    )

    # From pdf_generator: always ends
    workflow.add_edge("pdf_generator", END)

    # Compile the graph
    compiled = workflow.compile(checkpointer=checkpointer)

    LOGGER.info("Transport optimizer graph compiled successfully")

    return compiled


def get_initial_state(language: str = "en") -> TransportOptimizerState:
    """Get the initial state for a new transport optimizer session.

    Args:
        language: Output language for responses

    Returns:
        Initial state dictionary
    """
    return {
        "messages": [],
        "summary_message": None,
        "next_agent": "route_collector",
        "city": "",
        "starting_point": "",
        "route_pairs": [],
        "pairs_confirmed": False,
        "transport_overview": {},
        "transport_overview_complete": False,
        "place_coordinates": {},  # Cached coordinates by place name
        "transport_options": {},
        "user_preferences": [],
        "current_pair_index": 0,
        "all_preferences_collected": False,
        "paid_routes": [],
        "route_cost_analyses": [],
        "payment_methods_info": [],
        "transport_apps": [],
        "final_pdf_path": "",
        "language": language,
        "interaction_complete": False,
        "handoff_called": False,
    }
