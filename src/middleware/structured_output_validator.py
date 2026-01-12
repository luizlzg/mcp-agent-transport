"""
Structured Output Validator Middleware for LangChain 1.0

This middleware validates structured outputs from agents and retries with error feedback if validation fails.

Based on LangChain 1.0 middleware architecture:
- https://blog.langchain.com/agent-middleware/
- https://docs.langchain.com/oss/python/langchain/middleware/built-in
"""
import os
from typing import Any, Dict, Optional, Callable
from langchain.agents.middleware import AgentMiddleware
from src.utils.logger import LOGGER
from src.agent.tools import _check_url_accessible


class StructuredOutputValidationError(Exception):
    """Exception raised when structured output validation fails."""

    def __init__(self, message: str, error_feedback_message: str, messages: list, state: Dict[str, Any]):
        """
        Initialize the exception.

        Args:
            message: Error message for logging
            error_feedback_message: Message to send back to the agent
            messages: All messages from the conversation so far
        """
        super().__init__(message)
        self.error_feedback_message = error_feedback_message
        self.messages = messages
        self.state = state


class StructuredOutputValidatorMiddleware(AgentMiddleware):
    """
    Middleware that validates structured output from agents.

    If validation fails:
    - Raises StructuredOutputValidationError with error message
    - Agent definition level handles retry logic

    Configuration:
    - MAX_RETRIES: Set via STRUCTURED_OUTPUT_MAX_RETRIES env var (default: 3)
    """

    def __init__(
        self,
        expected_schema: Dict[str, Any],
        validator_func: Optional[Callable[[Dict[str, Any]], tuple[bool, str]]] = None,
    ):
        """
        Initialize the middleware.

        Args:
            expected_schema: Dict describing the expected output schema (TypedDict structure)
            validator_func: Optional custom validation function that returns (is_valid, error_message)
        """
        self.expected_schema = expected_schema
        self.validator_func = validator_func or self._default_validator
        self.max_retries = int(os.getenv("STRUCTURED_OUTPUT_MAX_RETRIES", "3"))
        LOGGER.info(
            f"Initialized StructuredOutputValidatorMiddleware (max_retries={self.max_retries} at agent level)"
        )

    def _default_validator(
        self, output: Dict[str, Any], state: Dict[str, Any] = None
    ) -> tuple[bool, str]:
        """
        Default validation function - checks if all required keys are present.

        Args:
            output: The structured output to validate
            state: Optional state dict (not used in default validator)

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not isinstance(output, dict):
            return False, f"Output is not a dict, got {type(output).__name__}"

        missing_keys = []
        for key in self.expected_schema.__annotations__.keys():
            if key not in output:
                missing_keys.append(key)

        if missing_keys:
            return (
                False,
                f"Missing required fields: {', '.join(missing_keys)}. "
                f"Expected schema: {list(self.expected_schema.__annotations__.keys())}",
            )

        # Check for empty required fields
        empty_fields = []
        for key, value in output.items():
            if key in self.expected_schema:
                # Check if required list/string fields are empty
                if isinstance(value, (list, str)) and not value:
                    empty_fields.append(key)

        if empty_fields:
            return (
                False,
                f"Required fields are empty: {', '.join(empty_fields)}. "
                f"Please provide values for all required fields.",
            )

        return True, ""

    def after_agent(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hook that runs after model call - validates structured output.

        This is the main middleware hook for LangChain 1.0.

        Args:
            state: Current agent state containing messages and output

        Returns:
            Updated state if validation passes

        Raises:
            StructuredOutputValidationError: If validation fails (includes messages from state)
        """
        LOGGER.info("Running StructuredOutputValidatorMiddleware.after_agent")

        # Skip validation if input was marked as invalid
        if state.get("invalid_input", False):
            LOGGER.info("⏭️ Skipping structured output validation - input marked as invalid")
            return state

        # Extract structured output from state
        structured_output = state.get("structured_response")
        if not structured_output:
            LOGGER.warning("No structured_response found in state")

            # Get messages from state
            messages = state.get("messages", [])

            # Create error feedback message asking the agent to generate structured output
            error_feedback_message = f"""
CRITICAL: You have NOT generated the required structured output yet!

After completing your research with the tools, you MUST generate the final DayResearchResult structure.

{{
  "attractions": [
    {{
      "name": "Attraction Name",
      "day_number": 1,
      "description": "Detailed 150-300 word description...",
      "images": [
        {{"id": "img1", "url_regular": "https://...", "caption": "Description of image"}}
      ],
      "ticket_info": [
        {{"title": "Ticket Type", "content": "Price details", "url": "https://official-site.com/tickets"}}
      ],
      "useful_links": [
        {{"title": "Official Site", "url": "https://..."}}
      ],
      "estimated_cost": 25.0,
      "currency": "EUR"
    }}
  ]
}}

Generate this structured output NOW based on the research you already did.
"""

            # Raise error with messages - agent definition will handle retry
            raise StructuredOutputValidationError(
                "No structured_response found in state",
                error_feedback_message,
                messages,
                state
            )

        # Validate the output (pass state to validator for attraction coverage check)
        is_valid, error_message = self.validator_func(structured_output, state)

        if is_valid:
            LOGGER.info("✅ Structured output validation passed")
            return state

        # Validation failed - raise error with feedback message
        LOGGER.warning(f"⚠️ Structured output validation failed: {error_message}")

        # Get messages from state
        messages = state.get("messages", [])

        # Create error feedback message for the agent
        error_feedback_message = f"""
ATTENTION: The previous response was not in the correct format.

Error found: {error_message}

Please provide the response AGAIN in the correct structured format.
Make sure to include ALL required fields.
"""

        # Raise error with messages - agent definition will handle retry
        raise StructuredOutputValidationError(
            f"Structured output validation failed: {error_message}",
            error_feedback_message,
            messages,
            state
        )


# Validation functions for specific schemas

def validate_organized_itinerary(output: Dict[str, Any], state: Dict[str, Any] = None) -> tuple[bool, str]:
    """
    Validate OrganizedItinerary schema.

    Expected:
    - document_title (str)
    - attractions_by_day (list of dicts with "day" and "attractions")
    """
    if not isinstance(output, dict):
        return False, f"Output must be a dict, got {type(output).__name__}"

    # Check document_title
    if "document_title" not in output:
        return False, "Missing 'document_title' field"

    if not output["document_title"] or not isinstance(output["document_title"], str):
        return False, "'document_title' must be a non-empty string"

    # Check attractions_by_day
    if "attractions_by_day" not in output:
        return False, "Missing 'attractions_by_day' field"

    attractions_by_day = output["attractions_by_day"]
    if not isinstance(attractions_by_day, list):
        return False, "'attractions_by_day' must be a list"

    if not attractions_by_day:
        return False, "'attractions_by_day' cannot be empty"

    # Validate each day
    for idx, day in enumerate(attractions_by_day):
        if not isinstance(day, dict):
            return False, f"Day at index {idx} must be a dict"

        if "day" not in day:
            return False, f"Day at index {idx} missing 'day' field"

        if "attractions" not in day:
            return False, f"Day at index {idx} missing 'attractions' field"

        if not isinstance(day["attractions"], list):
            return False, f"Day {day.get('day')} 'attractions' must be a list"

        if not day["attractions"]:
            return False, f"Day {day.get('day')} 'attractions' cannot be empty"

    return True, ""


def validate_day_research_result(output: Dict[str, Any], state: Dict[str, Any] = None) -> tuple[bool, str]:
    """
    Validate DayResearchResult schema.

    Expected:
    - day_number (int)
    - attractions (list of AttractionResearchResult dicts)

    Also validates that all attractions from attraction_coordinates (if in state)
    have been documented by comparing attraction_key values.
    """
    if not isinstance(output, dict):
        return False, f"Output must be a dict, got {type(output).__name__}"

    # Check attractions
    if "attractions" not in output:
        return False, "Missing 'attractions' field"

    attractions = output["attractions"]
    if not isinstance(attractions, list):
        return False, "'attractions' must be a list"

    if not attractions:
        return False, "'attractions' cannot be empty - must research all attractions for this day"

    # First pass: check required fields and empty images
    required_fields = ["name", "attraction_key", "day_number", "description", "images", "estimated_cost"]
    for idx, attraction in enumerate(attractions):
        if not isinstance(attraction, dict):
            return False, f"Attraction at index {idx} must be a dict"

        for field in required_fields:
            if field not in attraction:
                return False, f"Attraction at index {idx} missing '{field}' field"

        if not attraction["name"]:
            return False, f"Attraction at index {idx} 'name' cannot be empty"

        images = attraction.get("images", [])
        if not images:
            attraction_name = attraction.get("name", f"at index {idx}")
            return False, f"Attraction '{attraction_name}' has no images. You MUST search images for ALL attractions using search_attraction_images tool. Search for images of '{attraction_name}' now."

    # Second pass: validate image URLs and collect all broken ones
    attractions_with_broken_images = []

    for attraction in attractions:
        attraction_name = attraction.get("name", "Unknown")
        images = attraction.get("images", [])

        all_broken = True
        broken_urls = []

        for img in images:
            url = img.get("url_regular", "")
            is_accessible, error_message = _check_url_accessible(url, timeout=5)

            if is_accessible:
                all_broken = False
                LOGGER.info(f"✅ Image URL accessible for '{attraction_name}': {url}")
            else:
                broken_urls.append((url, error_message))
                LOGGER.warning(f"❌ Image URL broken for '{attraction_name}': {url} - {error_message}")

        if all_broken and broken_urls:
            error_details = ", ".join([f"{url} ({err})" for url, err in broken_urls[:3]])
            attractions_with_broken_images.append({
                "name": attraction_name,
                "error_details": error_details
            })

    # Return error if any attractions have all broken images
    if attractions_with_broken_images:
        error_lines = []
        for item in attractions_with_broken_images:
            error_lines.append(f"- '{item['name']}': {item['error_details']}")

        return False, (
            f"All images are broken/inaccessible for {len(attractions_with_broken_images)} attraction(s):\n"
            f"{chr(10).join(error_lines)}\n\n"
            f"Use search_attraction_images to search for new images for each of these attractions."
        )

    # Check ticket_info URLs are accessible - only for PAID attractions
    # Free attractions should have empty ticket_info []
    for idx, attraction in enumerate(attractions):
        ticket_info = attraction.get("ticket_info", [])
        attraction_name = attraction.get("name", f"at index {idx}")

        for info in ticket_info:
            if not isinstance(info, dict):
                continue

            url = info.get("url", "")

            # URL must not be empty for paid attractions
            if not url:
                ticket_title = info.get("title", "Unknown")
                return False, (
                    f"Ticket info for '{attraction_name}' ({ticket_title}) has an empty URL. "
                    f"If this is a FREE attraction, remove the ticket_info entry and just mention 'Free entry' in the description. "
                    f"If this is a PAID attraction, use search_ticket_link to find an official ticket URL."
                )

            # Check if URL is accessible
            is_accessible, error_message = _check_url_accessible(url)
            if not is_accessible:
                ticket_title = info.get("title", "Unknown")
                return False, (
                    f"Ticket link for '{attraction_name}' ({ticket_title}) is broken: {url} - {error_message}. "
                    f"Use search_ticket_link with a different query to find a working official ticket URL."
                )

    # Check all attractions for this day were documented (if state provided)
    if state:
        # Get attractions for THIS day (not all attractions)
        attractions_by_day = state.get("attractions_by_day", [])
        day_number = attractions[0].get("day_number", None)
        attractions_list = []
        for day_attraction in attractions_by_day:
            if day_attraction.get("day") == day_number:
                attractions_list = day_attraction.get("attractions", [])
                break
        if attractions_list:
            expected_keys = set(attractions_list)
            documented_keys = {attr.get("attraction_key", "") for attr in attractions}

            missing = expected_keys - documented_keys
            if missing:
                missing_list = list(missing)
                return False, (
                    f"Missing documentation for {len(missing_list)} attraction(s):\n"
                    + "\n".join([f"  - {name}" for name in missing_list])
                    + "\n\nFor EACH missing attraction above:\n"
                    "1. Use search_attraction_info to research detailed information\n"
                    "2. Use search_attraction_images to find high-quality images\n"
                    "3. For PAID attractions, use search_ticket_link to find official ticket URLs\n"
                    "4. Add the attraction to your output with attraction_key EXACTLY matching the name above\n\n"
                    "Do NOT skip any attraction. Research and document ALL of them."
                )

    return True, ""


class ClusteringToolValidatorMiddleware(AgentMiddleware):
    """
    Middleware that validates the day organizer agent follows the correct workflow:

    1. Extract coordinates using 'extract_coordinates'
    2. Organize attractions by day using 'organize_attractions_by_days'
    3. If flexible attractions exist (K-means used), request user approval via 'request_itinerary_approval'

    If the input is invalid, the agent should call 'return_invalid_input_error' instead.

    Raises an error if the workflow is not followed correctly.
    """

    def __init__(self):
        """Initialize the middleware."""
        self.max_retries = int(os.getenv("STRUCTURED_OUTPUT_MAX_RETRIES", "3"))
        self.valid_clustering_tools = ["organize_attractions_by_days"]
        self.approval_tools = ["request_itinerary_approval"]
        self.error_handling_tools = ["return_invalid_input_error"]
        LOGGER.info(
            f"Initialized ClusteringToolValidatorMiddleware (max_retries={self.max_retries} at agent level)"
        )

    def after_agent(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hook that runs after agent completes - validates workflow was followed.

        Checks:
        1. Organization tool or error tool was called
        2. If has_flexible_attractions=True, approval tool must be called

        Args:
            state: Current agent state containing messages

        Returns:
            Updated state if validation passes

        Raises:
            StructuredOutputValidationError: If workflow is not followed correctly
        """
        LOGGER.info("Running ClusteringToolValidatorMiddleware.after_agent")

        # Get messages from state
        messages = state.get("messages", [])

        # Check which tools were called
        organization_tool_called = False
        approval_tool_called = False
        error_tool_called = False

        for msg in messages:
            # Check if this is an AIMessage with tool_calls
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    tool_name = tool_call.get("name")
                    if tool_name in self.valid_clustering_tools:
                        organization_tool_called = True
                        LOGGER.info(f"✅ Organization tool '{tool_name}' was called")
                    elif tool_name in self.approval_tools:
                        approval_tool_called = True
                        LOGGER.info(f"✅ Approval tool '{tool_name}' was called")
                    elif tool_name in self.error_handling_tools:
                        error_tool_called = True
                        LOGGER.info(f"✅ Error handling tool '{tool_name}' was called")

        # If error tool was called, skip other validations
        if error_tool_called:
            LOGGER.info("Error handling tool was called - skipping other validations")
            return state

        # Check if organization tool was called
        if not organization_tool_called:
            LOGGER.warning("⚠️ Organization tool was not called")

            error_feedback_message = """
ATTENTION: You didn't use the organization tool.

You MUST use one of the following tools:
- 'organize_attractions_by_days': To organize attractions by days (valid input)
- 'return_invalid_input_error': To return an error message (invalid/unrelated input)

If the input contains tourist attractions:
1. Use 'organize_attractions_by_days' to organize the attractions

If the input is empty, unrelated, or doesn't contain attractions:
1. Use 'return_invalid_input_error' with an explanatory message

Please complete the flow correctly.
"""

            raise StructuredOutputValidationError(
                "Organization tool was not called",
                error_feedback_message,
                messages,
                state
            )

        # Check if approval is required (has_flexible_attractions=True)
        has_flexible_attractions = state.get("has_flexible_attractions", False)

        if has_flexible_attractions and not approval_tool_called:
            LOGGER.warning("⚠️ Flexible attractions exist but approval tool was not called")

            error_feedback_message = """
ATTENTION: You organized attractions with K-means (flexible attractions) but didn't request user approval.

When has_flexible_attractions=True (mode="kmeans" or mode="mixed"), you MUST:
1. Call 'request_itinerary_approval' to get user confirmation
2. If user requests changes, use 'update_itinerary_organization' to apply them
3. Call 'request_itinerary_approval' again until approved

Please call 'request_itinerary_approval' now to get user approval for the itinerary.
"""

            raise StructuredOutputValidationError(
                "Approval tool not called for flexible attractions",
                error_feedback_message,
                messages,
                state
            )

        LOGGER.info("✅ Workflow validation passed")
        return state


class ToolUsageValidatorMiddleware(AgentMiddleware):
    """
    Middleware that validates required search tools were called.

    Prevents hallucinations by ensuring search_attraction_info and
    search_attraction_images were called at least once.
    """

    def __init__(self, required_tools: Optional[list[str]] = None):
        self.required_tools = required_tools or ["search_attraction_info", "search_attraction_images"]
        LOGGER.info(f"Initialized ToolUsageValidatorMiddleware (required_tools={self.required_tools})")

    def after_agent(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Check if required tools were called in messages."""
        LOGGER.info("Running ToolUsageValidatorMiddleware.after_agent")

        messages = state.get("messages", [])

        # Collect all tool names that were called
        called_tools = set()
        for msg in messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    tool_name = tool_call.get("name")
                    if tool_name:
                        called_tools.add(tool_name)

        # Check which required tools are missing
        missing_tools = set(self.required_tools) - called_tools

        if missing_tools:
            error_feedback_message = f"""
CRITICAL: You did NOT use the required search tools!

Missing tools: {', '.join(missing_tools)}

You MUST call these tools:
- search_attraction_info: To research detailed information
- search_attraction_images: To find high-quality images

Do NOT skip this step or make up information.
"""
            LOGGER.warning(f"⚠️ Tool usage validation failed - missing: {missing_tools}")

            raise StructuredOutputValidationError(
                f"Required tools not called: {missing_tools}",
                error_feedback_message,
                messages,
                state
            )

        LOGGER.info("✅ Tool usage validation passed")
        return state
