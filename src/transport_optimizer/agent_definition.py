"""Agent definitions and node functions for the transport optimizer.

Consolidates all agent creation and node functions following the itinerary_generator pattern.

Following LangChain 1.0 patterns:
- Tools use Command to update state directly
- Agent uses create_agent from langchain.agents
- Node functions invoke agents and log messages
- Handoff is controlled by tools with return_direct=True
"""
import os
from datetime import datetime
from typing import Dict, Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain.agents import create_agent

from src.utils.logger import LOGGER
from src.transport_optimizer.state import TransportOptimizerState
from src.middleware import (
    HandoffToolValidatorMiddleware,
    HandoffToolValidationError,
)
from langchain.agents.middleware import SummarizationMiddleware
from src.transport_optimizer.tools import (
    ROUTE_COLLECTOR_TOOLS,
    TRANSPORT_OVERVIEW_TOOLS,
    TRANSPORT_RESEARCHER_TOOLS,
    COST_CALCULATOR_TOOLS,
)
from src.transport_optimizer.prompts import (
    ROUTE_COLLECTOR_PROMPT,
    TRANSPORT_OVERVIEW_PROMPT,
    TRANSPORT_RESEARCHER_PROMPT,
    COST_CALCULATOR_PROMPT,
)

summary_prompt = """Summarize this transport planning conversation in DETAIL. You MUST preserve:

1. **City/Location**: Which city is being navigated

2. **User's Full Itinerary**: ALL routes and places the user mentioned:
   - Every place they want to visit
   - The order of visits
   - Which day each route is planned for (if mentioned)
   - Starting point and final destination
   - Any intermediate stops

3. **All Route Pairs**: Every origin → destination pair with their index (0-based)

4. **Transport Options Found**: For each route, list ALL options with:
   - Mode (walking, subway, bus, etc.)
   - Duration in minutes
   - Distance in km
   - Any line numbers or transfer details

5. **User Preferences Selected**: For each route pair:
   - Which mode the user chose
   - Why they chose it (if mentioned)
   - The pair_index (0-based)

6. **User Travel Preferences & Constraints**: ALL preferences mentioned (CRITICAL - these guide future route decisions):
   - Walking preferences (e.g., "prefer walking if under X minutes")
   - Budget constraints (e.g., "keep costs under €X")
   - Time preferences (e.g., "prefer faster options")
   - Comfort preferences (e.g., "avoid crowded transport")
   - Accessibility requirements
   - Weather considerations
   - Any other travel rules the user stated

7. **Costs Researched**: Any pricing information found:
   - Single ticket prices
   - Day pass prices
   - Payment methods mentioned

8. **Current Progress**: Which route pairs are done, which are pending

IMPORTANT: User travel preferences and constraints MUST be preserved exactly as stated - they should guide all future route recommendations in this conversation.

Be detailed and complete. This summary will be used to continue the conversation.

Messages to summarize:
{messages}

"""

# ============================================================================
# LLM Initialization
# ============================================================================

def _initialize_llm(model_name: str = None, temperature: float = 0) -> ChatOpenAI:
    """Initialize the LLM for an agent.

    Args:
        model_name: Model name to use (defaults to env var or claude-sonnet)
        temperature: Temperature for generation (default 0)

    Returns:
        Configured ChatOpenAI instance
    """
    model = model_name or os.getenv("MODEL_NAME", "anthropic/claude-sonnet-4-20250514")
    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable is required")

    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        temperature=temperature,
    )


# ============================================================================
# Route Collector Agent
# ============================================================================

def create_route_collector_agent(model_name: str = None, language: str = "en"):
    """Create the route collector agent."""
    model = model_name or os.getenv("ROUTE_COLLECTOR_MODEL") or os.getenv("MODEL_NAME", "anthropic/claude-sonnet-4-20250514")
    llm = _initialize_llm(model_name=model)

    handoff_validator = HandoffToolValidatorMiddleware(
        agent_type="route_collector",
        handoff_tools=["confirm_route_pairs"]
    )

    agent = create_agent(
        model=llm,
        tools=ROUTE_COLLECTOR_TOOLS,
        system_prompt=ROUTE_COLLECTOR_PROMPT.format(language=language),
        state_schema=TransportOptimizerState,
        middleware=[
            SummarizationMiddleware(
                model=_initialize_llm(model_name=os.getenv("SUMMARIZATION_MODEL") or model),
                trigger=("tokens", 200000),
                summary_prompt=summary_prompt,
            ),
            handoff_validator
        ],
    )

    return agent


def route_collector_node(state: TransportOptimizerState) -> Dict[str, Any]:
    """Node function for the route collector agent.

    This agent:
    1. Processes user messages to extract route information
    2. Searches for place coordinates (saved to place_coordinates state)
    3. Registers route pairs using place names (coordinates retrieved from state)
    4. Hands off to transport_researcher (via confirm_route_pairs tool with return_direct=True)

    Tools handle all state updates via Command.

    Args:
        state: Current graph state

    Returns:
        State updates (messages only - other updates come from tools via Command)
    """
    LOGGER.info("=" * 60)
    LOGGER.info("RUNNING ROUTE COLLECTOR AGENT")
    LOGGER.info("=" * 60)

    # Get current state values
    messages = state.get("messages", [])
    summary_message = state.get("summary_message", None)
    summary_message_index = messages.index(summary_message) if summary_message in messages else 0
    messages = messages[summary_message_index:]  # Only keep messages after summary
    route_pairs = state.get("route_pairs", [])
    pairs_confirmed = state.get("pairs_confirmed", False)
    city = state.get("city", "")

    # If pairs are already confirmed, hand off to next agent
    if pairs_confirmed:
        LOGGER.info("Pairs already confirmed, handing off to transport_researcher")
        return {
            "next_agent": "transport_researcher",
            "current_pair_index": 0,
            "messages": [HumanMessage(content="Ok, all my routes are confirmed. Show me the transport options.")],
        }

    # Get model config from environment
    model_name = os.getenv("ROUTE_COLLECTOR_MODEL") or os.getenv("MODEL_NAME", "anthropic/claude-sonnet-4-20250514")
    language = state.get("language", "en")

    # Create and invoke the agent
    max_retries = int(os.getenv("HANDOFF_VALIDATION_MAX_RETRIES", "3"))

    try:
        agent = create_route_collector_agent(model_name=model_name, language=language)

        # Build the conversation context
        agent_messages = []
        for msg in messages:
            if isinstance(msg, (HumanMessage, AIMessage, ToolMessage)):
                agent_messages.append(msg)
        if agent_messages and isinstance(agent_messages[-1], HumanMessage):
            LOGGER.info(f"{agent_messages[-1].pretty_repr()}")

        # Add minimal context (only non-inferable state)
        context_parts = []
        if city:
            context_parts.append(f"Current city: {city}")
        if route_pairs:
            pairs_str = "\n".join([f"  {i+1}. {p['start_place']} -> {p['end_place']}"
                                  for i, p in enumerate(route_pairs)])
            context_parts.append(f"Route pairs collected so far:\n{pairs_str}")

        if context_parts:
            context_msg = "\n".join(context_parts)
            # Add as system context if not already present
            agent_messages.append(SystemMessage(content=f"[Context]\n{context_msg}"))

        state["messages"] = agent_messages

        # Stream the agent with retry logic for handoff validation
        seen_messages = []
        final_event = {}

        for retry_count in range(max_retries):
            try:
                # Track final state to forward all updates from tools via Command
                for event in agent.stream(state, stream_mode="values"):
                    # Log messages from state
                    for msg in event.get("messages", []):
                        if msg not in agent_messages and msg not in seen_messages:
                            seen_messages.append(msg)
                            LOGGER.info(msg.pretty_repr())
                    final_event = event

                # If we get here, no HandoffToolValidationError was raised
                break

            except HandoffToolValidationError as e:
                LOGGER.warning(f"Handoff validation failed (attempt {retry_count + 1}/{max_retries}): {e}")

                if retry_count < max_retries - 1:
                    # Add error feedback to messages and retry
                    error_msg = HumanMessage(content=e.error_feedback_message)
                    agent_messages = e.messages + [error_msg]
                    state["messages"] = agent_messages
                    LOGGER.info(f"Retrying with error feedback...")
                else:
                    # Max retries reached, return with error
                    LOGGER.error(f"Max retries reached for handoff validation")
                    error_msg = AIMessage(content="I apologize, but I'm having trouble completing this step. Please try again.")
                    return {
                        "messages": [error_msg],
                        "next_agent": "end",
                    }

        LOGGER.info("=" * 60)

        state_update = {"messages": final_event.get("messages", []), "summary_message": final_event.get("messages", [])[0] if final_event.get("messages") else None}

        # Forward state updates from tools via Command
        # Route collector tools can update: place_coordinates, route_pairs, city, pairs_confirmed, current_pair_index
        for key in ["place_coordinates", "route_pairs", "city", "pairs_confirmed", "current_pair_index"]:
            if key in final_event and final_event[key] != state.get(key):
                state_update[key] = final_event[key]
                LOGGER.info(f"Forwarding state update: {key}")

        # Determine next_agent: preserve tool's value or default to "end" for user input
        tool_next_agent = final_event.get("next_agent")
        if tool_next_agent and tool_next_agent != "route_collector":
            LOGGER.info(f"Tool requested handoff to: {tool_next_agent}")
            state_update["next_agent"] = tool_next_agent
            # Add HumanMessage so next agent has something to respond to
            if tool_next_agent == "transport_researcher":
                state_update["messages"] = state_update["messages"] + [
                    HumanMessage(content="Ok, all my routes are confirmed. Show me the transport options.")
                ]
        else:
            state_update["next_agent"] = "end"

        return state_update

    except Exception as e:
        LOGGER.error(f"Error in route_collector_node: {e}")
        error_msg = AIMessage(content=f"I encountered an error: {str(e)}. Could you please try again?")
        return {
            "messages": [error_msg],
            "next_agent": "end",  # End iteration to wait for user input
        }


# ============================================================================
# Transport Overview Agent (silent, general cost research — runs once)
# ============================================================================

def create_transport_overview_agent(model_name: str = None, language: str = "en"):
    """Create the transport overview agent."""
    model = model_name or os.getenv("TRANSPORT_OVERVIEW_MODEL") or os.getenv("MODEL_NAME", "anthropic/claude-sonnet-4-20250514")
    llm = _initialize_llm(model_name=model, temperature=0)

    handoff_validator = HandoffToolValidatorMiddleware(
        agent_type="transport_overview",
        handoff_tools=["finish_transport_overview"]
    )

    agent = create_agent(
        model=llm,
        tools=TRANSPORT_OVERVIEW_TOOLS,
        system_prompt=TRANSPORT_OVERVIEW_PROMPT.format(language=language),
        state_schema=TransportOptimizerState,
        middleware=[
            SummarizationMiddleware(
                model=_initialize_llm(model_name=os.getenv("SUMMARIZATION_MODEL") or model),
                trigger=("tokens", 200000),
                summary_prompt=summary_prompt,
            ),
            handoff_validator,
        ],
    )

    return agent


def transport_overview_node(state: TransportOptimizerState) -> Dict[str, Any]:
    """Node function for the transport overview agent.

    Silent research step that runs once after routes are confirmed and before
    route research. It researches the city's general transport cost/ticketing
    model, saves a summary (via register_transport_overview), and hands off to
    the transport researcher (via finish_transport_overview). It never waits for
    user input — it always auto-continues to transport_researcher.

    Args:
        state: Current graph state

    Returns:
        State updates (messages + transport_overview + next_agent)
    """
    LOGGER.info("=" * 60)
    LOGGER.info("RUNNING TRANSPORT OVERVIEW AGENT")
    LOGGER.info("=" * 60)

    # If overview already done, hand off immediately (defensive)
    if state.get("transport_overview_complete", False):
        LOGGER.info("Transport overview already complete, handing off to transport_researcher")
        return {"next_agent": "transport_researcher"}

    messages = state.get("messages", [])
    summary_message = state.get("summary_message", None)
    summary_message_index = messages.index(summary_message) if summary_message in messages else 0
    messages = messages[summary_message_index:]  # Only keep messages after summary
    city = state.get("city", "")

    model_name = os.getenv("TRANSPORT_OVERVIEW_MODEL") or os.getenv("MODEL_NAME", "anthropic/claude-sonnet-4-20250514")
    language = state.get("language", "en")

    max_retries = int(os.getenv("HANDOFF_VALIDATION_MAX_RETRIES", "3"))

    try:
        agent = create_transport_overview_agent(model_name=model_name, language=language)

        # Build the conversation context
        agent_messages = []
        for msg in messages:
            if isinstance(msg, (HumanMessage, AIMessage, ToolMessage)):
                agent_messages.append(msg)

        context_parts = []
        if city:
            context_parts.append(f"City: {city}")
        context_parts.append(
            "Research the general transport cost/ticketing model for this city now, "
            "then register the overview and finish. Do not ask the user anything."
        )
        context_msg = "\n".join(context_parts)
        # Drive the silent run with an explicit instruction turn
        agent_messages.append(HumanMessage(content=f"[Context]\n{context_msg}"))

        state["messages"] = agent_messages

        seen_messages = []
        final_event = {}

        for retry_count in range(max_retries):
            try:
                for event in agent.stream(state, stream_mode="values"):
                    for msg in event.get("messages", []):
                        if msg not in agent_messages and msg not in seen_messages:
                            seen_messages.append(msg)
                            LOGGER.info(msg.pretty_repr())
                    final_event = event
                break

            except HandoffToolValidationError as e:
                LOGGER.warning(f"Handoff validation failed (attempt {retry_count + 1}/{max_retries}): {e}")
                if retry_count < max_retries - 1:
                    error_msg = HumanMessage(content=e.error_feedback_message)
                    agent_messages = e.messages + [error_msg]
                    state["messages"] = agent_messages
                    LOGGER.info("Retrying with error feedback...")
                else:
                    # Even if the handoff wasn't validated, force progress to route research
                    LOGGER.error("Max retries reached for transport overview handoff; forcing handoff")
                    break

        LOGGER.info("=" * 60)

        state_update = {
            "messages": final_event.get("messages", []),
            "summary_message": final_event.get("messages", [])[0] if final_event.get("messages") else None,
        }

        # Forward the overview produced by the tools
        for key in ["transport_overview", "transport_overview_complete"]:
            if key in final_event and final_event[key] != state.get(key):
                state_update[key] = final_event[key]
                LOGGER.info(f"Forwarding state update: {key}")

        # This step is silent: always continue to transport_researcher (never "end")
        state_update["next_agent"] = "transport_researcher"
        state_update["transport_overview_complete"] = True
        return state_update

    except Exception as e:
        LOGGER.error(f"Error in transport_overview_node: {e}")
        # Don't block the pipeline on overview failure — continue to route research
        return {
            "next_agent": "transport_researcher",
            "transport_overview_complete": True,
        }


# ============================================================================
# Transport Researcher Agent
# ============================================================================

def create_transport_researcher_agent(model_name: str = None, language: str = "en"):
    """Create the transport researcher agent."""
    model = model_name or os.getenv("TRANSPORT_RESEARCHER_MODEL") or os.getenv("MODEL_NAME", "anthropic/claude-sonnet-4-20250514")
    llm = _initialize_llm(model_name=model)

    handoff_validator = HandoffToolValidatorMiddleware(
        agent_type="transport_researcher",
        handoff_tools=["finish_transport_research"]
    )

    agent = create_agent(
        model=llm,
        tools=TRANSPORT_RESEARCHER_TOOLS,
        system_prompt=TRANSPORT_RESEARCHER_PROMPT.format(language=language),
        state_schema=TransportOptimizerState,
        middleware=[
            SummarizationMiddleware(
                model=_initialize_llm(model_name=os.getenv("SUMMARIZATION_MODEL") or model),
                trigger=("tokens", 200000),
                summary_prompt=summary_prompt,
            ),
        ],
    )

    return agent


def transport_researcher_node(state: TransportOptimizerState) -> Dict[str, Any]:
    """Node function for the transport researcher agent.

    This agent:
    1. Gets transport options for each route pair (via get_transport_options with place names)
    2. Presents options to the user
    3. Records user preferences with currency (via register_user_preference)
    4. Hands off to cost_calculator (via finish_transport_research tool with return_direct=True)

    Tools handle all state updates via Command.

    Args:
        state: Current graph state

    Returns:
        State updates (messages only - tools handle state via Command)
    """
    LOGGER.info("=" * 60)
    LOGGER.info("RUNNING TRANSPORT RESEARCHER AGENT")
    LOGGER.info("=" * 60)

    # Get current state values
    messages = state.get("messages", [])
    summary_message = state.get("summary_message", None)
    summary_message_index = messages.index(summary_message) if summary_message in messages else 0
    messages = messages[summary_message_index:]  # Only keep messages after summary
    route_pairs = state.get("route_pairs", [])
    user_preferences = state.get("user_preferences", [])
    current_pair_index = state.get("current_pair_index", 0)
    all_preferences_collected = state.get("all_preferences_collected", False)

    # If all preferences collected, hand off to cost calculator
    if all_preferences_collected or current_pair_index >= len(route_pairs):
        LOGGER.info("All preferences collected, handing off to cost_calculator")
        return {
            "next_agent": "cost_calculator",
            "all_preferences_collected": True,
            "messages": [HumanMessage(content="I've selected transport for all routes. Please research the costs.")],
        }

    # Get model config from environment
    model_name = os.getenv("TRANSPORT_RESEARCHER_MODEL") or os.getenv("MODEL_NAME", "anthropic/claude-sonnet-4-20250514")
    language = state.get("language", "en")

    # Create and invoke the agent
    max_retries = int(os.getenv("HANDOFF_VALIDATION_MAX_RETRIES", "3"))

    try:
        agent = create_transport_researcher_agent(model_name=model_name, language=language)

        # Build the conversation context
        agent_messages = []
        for msg in messages:
            if isinstance(msg, (HumanMessage, AIMessage, ToolMessage)):
                agent_messages.append(msg)
        if agent_messages and isinstance(agent_messages[-1], HumanMessage):
            LOGGER.info(f"{agent_messages[-1].pretty_repr()}")

        # Add minimal context (only essential non-inferable state)
        context_parts = []

        # General transport overview (for estimated per-option pricing)
        transport_overview = state.get("transport_overview", {})
        if transport_overview and transport_overview.get("summary"):
            context_parts.append(
                "General transport overview (use it to show estimated prices per option):\n"
                f"{transport_overview['summary']}"
            )

        # Show current progress (0-based indexing)
        context_parts.append(f"Currently processing pair {current_pair_index} of {len(route_pairs)} (0-indexed, so pairs are 0 to {len(route_pairs) - 1})")

        # Show current pair details
        if current_pair_index < len(route_pairs):
            current_pair = route_pairs[current_pair_index]
            context_parts.append(f"Current pair: {current_pair['start_place']} -> {current_pair['end_place']}")

        # Show already collected preferences summary
        if user_preferences:
            prefs_str = "\n".join([f"  - Pair {p['pair_index']}: {p['selected_mode']}"
                                  for p in user_preferences])
            context_parts.append(f"Preferences already collected:\n{prefs_str}")

        context_msg = "\n".join(context_parts)
        agent_messages.append(SystemMessage(content=f"[Context]\n{context_msg}"))

        LOGGER.info(f"Processing pair {current_pair_index}: {route_pairs[current_pair_index]['start_place']} -> {route_pairs[current_pair_index]['end_place']}")

        state["messages"] = agent_messages

        # Stream the agent with retry logic for handoff validation
        seen_messages = []
        final_event = {}

        for retry_count in range(max_retries):
            try:
                # Track final state to forward all updates from tools via Command
                for event in agent.stream(state, stream_mode="values"):
                    # Log messages from state
                    for msg in event.get("messages", []):
                        if msg not in agent_messages and msg not in seen_messages:
                            seen_messages.append(msg)
                            LOGGER.info(msg.pretty_repr())
                    final_event = event

                # If we get here, no HandoffToolValidationError was raised
                break

            except HandoffToolValidationError as e:
                LOGGER.warning(f"Handoff validation failed (attempt {retry_count + 1}/{max_retries}): {e}")

                if retry_count < max_retries - 1:
                    # Add error feedback to messages and retry
                    error_msg = HumanMessage(content=e.error_feedback_message)
                    agent_messages = e.messages + [error_msg]
                    state["messages"] = agent_messages
                    LOGGER.info(f"Retrying with error feedback...")
                else:
                    # Max retries reached, return with error
                    LOGGER.error(f"Max retries reached for handoff validation")
                    error_msg = AIMessage(content="I apologize, but I'm having trouble completing this step. Please try again.")
                    return {
                        "messages": [error_msg],
                        "next_agent": "end",
                    }

        LOGGER.info("=" * 60)

        # Build state update dict, forwarding all relevant updates from tools
        state_update = {"messages": final_event.get("messages", []), "summary_message": final_event.get("messages", [])[0] if final_event.get("messages") else None}

        # Forward state updates from tools via Command
        # Transport researcher tools can update: user_preferences, current_pair_index, all_preferences_collected, transport_options
        for key in ["user_preferences", "current_pair_index", "all_preferences_collected", "transport_options"]:
            if key in final_event and final_event[key] != state.get(key):
                state_update[key] = final_event[key]
                LOGGER.info(f"Forwarding state update: {key}")

        # Determine next_agent: preserve tool's value or default to "end" for user input
        tool_next_agent = final_event.get("next_agent")
        if tool_next_agent and tool_next_agent != "transport_researcher":
            LOGGER.info(f"Tool requested handoff to: {tool_next_agent}")
            state_update["next_agent"] = tool_next_agent
            # Add HumanMessage so next agent has something to respond to
            if tool_next_agent == "cost_calculator":
                state_update["messages"] = state_update["messages"] + [
                    HumanMessage(content="I've selected transport for all routes. Please research the costs.")
                ]
        else:
            state_update["next_agent"] = "end"

        return state_update

    except Exception as e:
        LOGGER.error(f"Error in transport_researcher_node: {e}")
        error_msg = AIMessage(content=f"I encountered an error: {str(e)}. Could you please try again?")
        return {
            "messages": [error_msg],
            "next_agent": "end",  # End iteration to wait for user input
        }


# ============================================================================
# Cost Calculator Agent
# ============================================================================

def create_cost_calculator_agent(model_name: str = None, language: str = "en"):
    """Create the cost calculator agent."""
    model = model_name or os.getenv("COST_CALCULATOR_MODEL") or os.getenv("MODEL_NAME", "anthropic/claude-sonnet-4-20250514")
    llm = _initialize_llm(model_name=model, temperature=0)

    handoff_validator = HandoffToolValidatorMiddleware(
        agent_type="cost_calculator",
        handoff_tools=["finish_interaction"]
    )

    agent = create_agent(
        model=llm,
        tools=COST_CALCULATOR_TOOLS,
        system_prompt=COST_CALCULATOR_PROMPT.format(language=language, today_date=datetime.now().strftime("%Y-%m-%d")),
        state_schema=TransportOptimizerState,
        middleware=[
            SummarizationMiddleware(
                model=_initialize_llm(model_name=os.getenv("SUMMARIZATION_MODEL") or model),
                trigger=("tokens", 200000),
                summary_prompt=summary_prompt,
            ),
            handoff_validator
        ],
    )

    return agent


def cost_calculator_node(state: TransportOptimizerState) -> Dict[str, Any]:
    """Node function for the cost calculator agent.

    This agent:
    1. Determines paid routes from user_preferences (non-walking modes)
    2. Researches pricing information (via search_transport_information tool)
    3. Registers cost info (via register_cost_info tool -> Command updates state)
    4. Sets recommendation (via set_recommendation tool -> Command updates state)
    5. Generates PDF (via generate_route_pdf tool -> Command updates state)
    6. Finishes interaction (via finish_interaction tool with return_direct=True)

    Tools handle all state updates via Command.

    Args:
        state: Current graph state

    Returns:
        State updates (messages only - tools handle state via Command)
    """
    LOGGER.info("=" * 60)
    LOGGER.info("RUNNING COST CALCULATOR AGENT")
    LOGGER.info("=" * 60)

    # Get current state values
    messages = state.get("messages", [])
    summary_message = state.get("summary_message", None)
    summary_message_index = messages.index(summary_message) if summary_message in messages else 0
    messages = messages[summary_message_index:]  # Only keep messages after summary
    user_preferences = state.get("user_preferences", [])
    route_pairs = state.get("route_pairs", [])
    transport_options = state.get("transport_options", {})
    route_cost_analyses = state.get("route_cost_analyses", [])
    payment_methods_info = state.get("payment_methods_info", [])
    transport_apps = state.get("transport_apps", [])
    transport_overview = state.get("transport_overview", {})
    city = state.get("city", "")
    interaction_complete = state.get("interaction_complete", False)

    # If interaction is complete, end the graph
    if interaction_complete:
        LOGGER.info("Interaction complete, ending graph")
        return {
            "next_agent": "end",
        }

    # Determine paid routes from user_preferences (non-walking modes)
    paid_preferences = [
        pref for pref in user_preferences
        if pref.get("selected_mode", "").lower() not in ["walking", "walk"]
    ]

    LOGGER.info(f"Paid routes: {len(paid_preferences)} of {len(user_preferences)} preferences")

    model_name = os.getenv("COST_CALCULATOR_MODEL") or os.getenv("MODEL_NAME", "anthropic/claude-sonnet-4-20250514")
    language = state.get("language", "en")

    # Create and invoke the agent
    max_retries = int(os.getenv("HANDOFF_VALIDATION_MAX_RETRIES", "3"))

    try:
        agent = create_cost_calculator_agent(model_name=model_name, language=language)

        # Build the conversation context
        agent_messages = []
        for msg in messages:
            if isinstance(msg, (HumanMessage, AIMessage, ToolMessage)):
                agent_messages.append(msg)
        if agent_messages and isinstance(agent_messages[-1], HumanMessage):
            LOGGER.info(f"{agent_messages[-1].pretty_repr()}")

        # Add per-route context for the cost calculator
        context_parts = []

        # City
        if city:
            context_parts.append(f"City: {city}")

        # General transport overview (apply its fare-integration / transfer rules)
        if transport_overview and transport_overview.get("summary"):
            context_parts.append(
                "General transport overview (apply its fare-integration and transfer rules):\n"
                f"{transport_overview['summary']}"
            )

        # Per-route details for each paid route
        if paid_preferences:
            context_parts.append("Paid routes to research:")
            for pref in paid_preferences:
                pair_idx = pref.get("pair_index", 0)
                if pair_idx < len(route_pairs):
                    pair = route_pairs[pair_idx]
                    details = pref.get("transport_details", {})
                    mode = pref.get("selected_mode", "")
                    duration = details.get("duration_minutes", "?")

                    route_desc = f"  Route {pair_idx}: {pair['start_place']} → {pair['end_place']}"
                    route_desc += f"\n    Selected mode: {mode}"
                    route_desc += f"\n    Duration: {duration} min"

                    # Include transit leg details if available
                    pair_options = transport_options.get(pair_idx, [])
                    for opt in pair_options:
                        if opt.get("mode", "").lower() == mode.lower():
                            opt_details = opt.get("details", "")
                            transit_details = opt.get("transit_details", [])
                            if opt_details:
                                route_desc += f"\n    Details: {opt_details}"
                            if transit_details:
                                legs_str = ", ".join([
                                    f"{t.get('type', '').lower()} {t.get('name', '')} ({t.get('departure_stop', '')} → {t.get('arrival_stop', '')})"
                                    for t in transit_details
                                ])
                                route_desc += f"\n    Transit legs: {legs_str}"
                            break

                    context_parts.append(route_desc)
        else:
            context_parts.append("All selected transport is free (walking)")

        # Already-researched route cost analyses (for resume)
        if route_cost_analyses:
            context_parts.append("Route costs already researched:")
            for rca in route_cost_analyses:
                context_parts.append(f"  Route {rca['pair_index']}: {rca['total_cost']} {rca['currency']} ({', '.join(rca['modes'])})")

        # Already-registered payment methods (for resume)
        if payment_methods_info:
            context_parts.append("Payment methods already registered:")
            for pm in payment_methods_info:
                context_parts.append(f"  - {pm['name']}")

        # Already-registered transport-tracking apps (for resume)
        if transport_apps:
            context_parts.append("Transport-tracking apps already registered:")
            for app in transport_apps:
                context_parts.append(f"  - {app['name']}")

        context_msg = "\n".join(context_parts)
        agent_messages.append(SystemMessage(content=f"[Context]\n{context_msg}"))

        state["messages"] = agent_messages

        # Stream the agent with retry logic for handoff validation
        seen_messages = []
        final_event = {}

        for retry_count in range(max_retries):
            try:
                # Track final state to forward all updates from tools via Command
                for event in agent.stream(state, stream_mode="values"):
                    # Log messages from state
                    for msg in event.get("messages", []):
                        if msg not in agent_messages and msg not in seen_messages:
                            seen_messages.append(msg)
                            LOGGER.info(msg.pretty_repr())
                    final_event = event

                # If we get here, no HandoffToolValidationError was raised
                break

            except HandoffToolValidationError as e:
                LOGGER.warning(f"Handoff validation failed (attempt {retry_count + 1}/{max_retries}): {e}")

                if retry_count < max_retries - 1:
                    # Add error feedback to messages and retry
                    error_msg = HumanMessage(content=e.error_feedback_message)
                    agent_messages = e.messages + [error_msg]
                    state["messages"] = agent_messages
                    LOGGER.info(f"Retrying with error feedback...")
                else:
                    # Max retries reached, return with error
                    LOGGER.error(f"Max retries reached for handoff validation")
                    error_msg = AIMessage(content="I apologize, but I'm having trouble completing this step. Please try again.")
                    return {
                        "messages": [error_msg],
                        "next_agent": "end",
                    }

        LOGGER.info("=" * 60)

        # Build state update dict, forwarding all relevant updates from tools
        state_update = {"messages": final_event.get("messages", []), "summary_message": final_event.get("messages", [])[0] if final_event.get("messages") else None}

        # Forward state updates from tools via Command
        # Cost calculator tools can update: route_cost_analyses, payment_methods_info, transport_apps, final_pdf_path, interaction_complete
        for key in ["route_cost_analyses", "payment_methods_info", "transport_apps", "final_pdf_path", "interaction_complete"]:
            if key in final_event and final_event[key] != state.get(key):
                state_update[key] = final_event[key]
                LOGGER.info(f"Forwarding state update: {key}")

        # Determine next_agent: preserve tool's value or default to "end" for user input
        tool_next_agent = final_event.get("next_agent")
        if tool_next_agent and tool_next_agent != "cost_calculator":
            LOGGER.info(f"Tool requested handoff to: {tool_next_agent}")
            state_update["next_agent"] = tool_next_agent
        else:
            state_update["next_agent"] = "end"

        return state_update

    except Exception as e:
        LOGGER.error(f"Error in cost_calculator_node: {e}")
        error_msg = AIMessage(content=f"I encountered an error: {str(e)}. Could you please try again?")
        return {
            "messages": [error_msg],
            "next_agent": "end",  # End iteration to wait for user input
        }


# ============================================================================
# PDF Generator Node (deterministic, no LLM)
# ============================================================================

def pdf_generator_node(state: TransportOptimizerState) -> Dict[str, Any]:
    """Deterministic node that generates the PDF summary.

    This node reads all accumulated state data and generates a PDF document.
    No LLM is involved — this is a pure data-to-PDF transformation.

    Args:
        state: Current graph state with all route, cost, and payment data

    Returns:
        State updates with pdf path, interaction_complete, and next_agent
    """
    LOGGER.info("=" * 60)
    LOGGER.info("RUNNING PDF GENERATOR NODE")
    LOGGER.info("=" * 60)

    from src.processor.pdf_processor import RoutePDFGenerator, PDF_LABELS

    route_pairs = state.get("route_pairs", [])
    user_preferences = state.get("user_preferences", [])
    route_cost_analyses = state.get("route_cost_analyses", [])
    payment_methods_info = state.get("payment_methods_info", [])
    transport_apps = state.get("transport_apps", [])
    city = state.get("city", "")
    language = state.get("language", "en")

    # Get language-specific title
    labels = PDF_LABELS.get(language, PDF_LABELS["en"])
    title = labels.get("title_prefix", "Transport Route")

    try:
        generator = RoutePDFGenerator()
        pdf_path = generator.create_document(
            title=title,
            route_pairs=route_pairs,
            preferences=user_preferences,
            route_cost_analyses=route_cost_analyses,
            payment_methods_info=payment_methods_info,
            transport_apps=transport_apps,
            city=city,
            language=language,
        )

        LOGGER.info(f"PDF generated successfully: {pdf_path}")

        return {
            "final_pdf_path": pdf_path,
            "interaction_complete": True,
            "next_agent": "end",
            "messages": [AIMessage(content="Your transport summary PDF has been generated successfully.")],
        }

    except Exception as e:
        LOGGER.error(f"Error generating PDF: {e}")
        return {
            "interaction_complete": True,
            "next_agent": "end",
            "messages": [AIMessage(content=f"PDF generation failed: {str(e)}. The interaction is now complete.")],
        }


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "create_route_collector_agent",
    "route_collector_node",
    "create_transport_overview_agent",
    "transport_overview_node",
    "create_transport_researcher_agent",
    "transport_researcher_node",
    "create_cost_calculator_agent",
    "cost_calculator_node",
    "pdf_generator_node",
]
