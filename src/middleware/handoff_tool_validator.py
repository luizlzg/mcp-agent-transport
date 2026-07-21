"""
Handoff Tool Validator Middleware for Transport Optimizer

Validates that agents call the required handoff tools before transitioning
to the next agent. Follows the same pattern as itinerary_generator middleware.
"""
import os
from typing import Dict, Any, List
from langchain.agents.middleware import AgentMiddleware
from src.utils.logger import LOGGER


class HandoffToolValidationError(Exception):
    """Exception raised when handoff tool validation fails."""

    def __init__(self, message: str, error_feedback_message: str, messages: list, state: Dict[str, Any]):
        super().__init__(message)
        self.error_feedback_message = error_feedback_message
        self.messages = messages
        self.state = state


class HandoffToolValidatorMiddleware(AgentMiddleware):
    """
    Middleware that validates required handoff tools were called.

    Each agent type has specific handoff tools that MUST be called
    to properly transition to the next agent:

    - route_collector: confirm_route_pairs
    - transport_researcher: finish_transport_research
    - cost_calculator: finish_interaction
    """

    def __init__(self, agent_type: str, handoff_tools: List[str]):
        """
        Initialize middleware for a specific agent type.

        Args:
            agent_type: Name of the agent (for logging)
            handoff_tools: List of tool names that trigger handoff
        """
        self.agent_type = agent_type
        self.handoff_tools = handoff_tools
        self.max_retries = int(os.getenv("HANDOFF_VALIDATION_MAX_RETRIES", "3"))
        LOGGER.info(f"Initialized HandoffToolValidatorMiddleware for {agent_type}")

    def after_agent(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate handoff tool was called if agent is transitioning.

        Only validates when next_agent is set to a different agent.
        """
        LOGGER.info(f"Running HandoffToolValidatorMiddleware.after_agent for {self.agent_type}")

        messages = state.get("messages", [])
        next_agent = state.get("next_agent", "")

        # Check if any handoff tool was called
        handoff_tool_called = False
        for msg in messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    tool_name = tool_call.get("name")
                    if tool_name in self.handoff_tools:
                        handoff_tool_called = True
                        LOGGER.info(f"✅ Handoff tool '{tool_name}' was called")
                        break
            if handoff_tool_called:
                break

        # If next_agent indicates transition but no handoff tool was called
        if next_agent and next_agent != self.agent_type and next_agent != "end" and not handoff_tool_called:
            LOGGER.warning(f"⚠️ Transitioning to {next_agent} without calling handoff tool")

            error_feedback_message = self._build_error_message()

            raise HandoffToolValidationError(
                f"Handoff tool not called for {self.agent_type}",
                error_feedback_message,
                messages,
                state
            )

        # Update state to track handoff was validated
        state["handoff_called"] = handoff_tool_called

        LOGGER.info(f"✅ Handoff validation passed for {self.agent_type}")
        return state

    def _build_error_message(self) -> str:
        """Build agent-specific error feedback message."""

        if self.agent_type == "route_collector":
            return """
ATTENTION: You are trying to hand off to the next agent without confirming the route pairs.

Before transitioning, you MUST:
1. Ask the user to confirm that all route pairs are complete
2. Call 'confirm_route_pairs' tool when the user confirms

Please call 'confirm_route_pairs' to properly complete this phase.
"""
        elif self.agent_type == "transport_overview":
            return """
ATTENTION: You are trying to hand off to route research without completing the transport overview.

Before transitioning, you MUST:
1. Research the city's general transport cost/ticketing model
2. Call 'register_transport_overview' with your summary and source links
3. Call 'finish_transport_overview' to complete this phase

Please call 'finish_transport_overview' to properly complete this phase.
"""
        elif self.agent_type == "transport_researcher":
            return """
ATTENTION: You are trying to hand off to the cost calculator without finishing transport research.

Before transitioning, you MUST:
1. Ensure all route pairs have user preferences registered
2. Call 'finish_transport_research' tool to complete this phase

Please call 'finish_transport_research' to properly complete this phase.
"""
        elif self.agent_type == "cost_calculator":
            return """
ATTENTION: You are trying to finish without properly completing the interaction.

Before finishing, you MUST:
1. Provide cost recommendations to the user
2. Call 'finish_interaction' tool to complete the workflow

Please call 'finish_interaction' to properly complete this workflow.
"""
        else:
            return f"""
ATTENTION: You must call the appropriate handoff tool before transitioning.

Required tools: {', '.join(self.handoff_tools)}
"""
