"""Custom summarization middleware for transport optimizer."""
from typing import Dict, Any, List

import tiktoken
from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import SystemMessage
from langgraph.graph.message import RemoveMessage, REMOVE_ALL_MESSAGES

from src.utils.logger import LOGGER


class TransportSummarizationMiddleware(AgentMiddleware):
    """Middleware that summarizes conversation when it gets too long."""

    def __init__(self, model, trigger_tokens: int = 80000, keep_messages: int = 10):
        self.model = model
        self.trigger_tokens = trigger_tokens
        self.keep_messages = keep_messages
        self._encoding = tiktoken.encoding_for_model("gpt-4")
        self._summarized = False  # Only summarize once per agent run

    def _count_tokens(self, messages: List) -> int:
        total = 0
        for msg in messages:
            content = str(msg.content) if hasattr(msg, 'content') else str(msg)
            total += len(self._encoding.encode(content))
        return total

    def before_model(self, state: Dict[str, Any], runtime) -> Dict[str, Any] | None:
        """Run before each model call - return state UPDATES dict or None."""
        if self._summarized:
            return None

        messages = state.get("messages", [])
        token_count = self._count_tokens(messages)

        LOGGER.info(f"Token count: {token_count}/{self.trigger_tokens}")

        if token_count > self.trigger_tokens and len(messages) > self.keep_messages:
            LOGGER.info(f"Summarizing conversation (tokens={token_count}, messages={len(messages)})")

            messages_to_summarize = messages[:-self.keep_messages]
            recent_messages = messages[-self.keep_messages:]

            summary = self._generate_summary(messages_to_summarize)
            self._summarized = True

            LOGGER.info(f"Summarization complete. Keeping {len(recent_messages)} recent messages.")

            return {
                "messages": [
                    SystemMessage(content=f"[Previous Conversation Summary]\n{summary}"),
                    *recent_messages,
                ]
            }

        return None

    def _generate_summary(self, messages: List) -> str:
        prompt = """Summarize this transport planning conversation in DETAIL. You MUST preserve:

1. **City/Location**: Which city is being navigated
2. **All Route Pairs**: Every origin → destination pair with their index (0-based)
3. **Transport Options Found**: For each route, list ALL options with:
   - Mode (walking, subway, bus, etc.)
   - Duration in minutes
   - Distance in km
   - Any line numbers or transfer details
4. **User Preferences Selected**: For each route pair:
   - Which mode the user chose
   - Why they chose it (if mentioned)
   - The pair_index (0-based)
5. **Costs Researched**: Any pricing information found:
   - Single ticket prices
   - Day pass prices
   - Payment methods mentioned
6. **User Requirements**: Any constraints mentioned:
   - Maximum walking time limits
   - Budget limits
   - Accessibility needs
7. **Current Progress**: Which route pairs are done, which are pending

Be detailed and complete. This summary will be used to continue the conversation.

Conversation:
{conversation}

Detailed Summary:"""

        conversation = "\n".join([
            f"{type(m).__name__}: {m.content}"
            for m in messages
            if hasattr(m, 'content')
        ])
        response = self.model.invoke(prompt.format(conversation=conversation))
        return response.content
