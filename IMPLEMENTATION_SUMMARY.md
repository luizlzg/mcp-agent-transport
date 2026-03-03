# Implementation: Real-Time Tool Call Streaming in Transport Optimizer

## Problem
Tool calls were not appearing in real-time in main.py. They only appeared when the agent sent a final AI message to the user (when next_agent="end").

## Root Cause
The issue was that nodes consume agent messages internally using `agent.stream()`. When a node streams the agent, it processes all messages and only returns the final state to the outer graph. The outer graph's `stream_mode="messages"` doesn't see individual messages that were consumed by the node - it only sees what the node returns as final output.

## Solution
Replaced `graph.stream()` with `graph.astream_events()` in main.py's transport optimizer loop.

### Key Changes

**File Modified:** `main.py`

**Lines Modified:** ~15-17, ~293-355

### 1. Added asyncio import (line 15)
```python
import asyncio
```

### 2. Replaced streaming logic (lines 293-355)

**Before:**
```python
for mode, event in graph.stream(current_state, config=config, stream_mode=["messages", "values"]):
    if mode == "messages":
        msg, metadata = event
        if isinstance(msg, AIMessage) and msg.tool_calls:
            # Show tool calls - only appeared with final message!
            ...
```

**After:**
```python
async def _process_stream():
    async for event in graph.astream_events(current_state, config=config, version="v2"):
        event_type = event.get("event", "")
        event_data = event.get("data", {})
        event_metadata = event.get("metadata", {})

        # Tool start event - show tool name IMMEDIATELY when called
        if event_type == "on_tool_start":
            tool_name = event_data.get("name", "unknown")
            friendly_msg = TOOL_MESSAGES.get(tool_name, f"🔧 {tool_name}...")
            console.print(f"[dim]{friendly_msg}[/dim]")

        # Chat model streaming - token-by-token output
        elif event_type == "on_chat_model_stream":
            chunk = event_data.get("chunk")
            if chunk and hasattr(chunk, "content"):
                console.print(chunk.content, end="", flush=True)

        # Messages event - handle AIMessage with tool_calls
        elif event_type == "messages" and isinstance(event_data, AIMessage):
            # Same logic as before
            ...

        # Chain end event - capture final state
        elif event_type == "on_chain_end" and event_metadata.get("langgraph_step") != "graph":
            current_state.update(event_data)
            ...

# Run async stream in sync context
asyncio.run(_process_stream())
```

## Event Types Handled

1. **`on_tool_start`** - Fires immediately when a tool is called
   - Extracts tool name: `event_data.get("name")`
   - Displays friendly message: 📍, ✅, 🚇, 💰, etc.

2. **`on_tool_end`** - Tool completed
   - Currently pass-through (can be extended for completion messages)

3. **`on_chat_model_stream`** - Token-by-token streaming
   - Streams AI responses as they're generated
   - Uses `console.print(content, end="", flush=True)` for real-time effect

4. **`messages`** - Full message events
   - Handles AIMessage with tool_calls (for compatibility)
   - Shows assistant text content (if not already streamed via tokens)

5. **`on_chain_end`** - Node completion
   - Updates `current_state` from event data
   - Checks for `interaction_complete` flag
   - Handles PDF generation completion

## Benefits

✅ **Real-time tool call display** - Tool names appear as soon as tools are invoked
✅ **Token-by-token streaming** - AI responses stream word-by-word
✅ **Preserved existing functionality** - All existing logic (seen_content, seen_tool_calls, TOOL_MESSAGES) maintained
✅ **No agent node changes** - Transport optimizer nodes already using correct streaming
✅ **No API changes** - API layer unaffected
✅ **Backward compatible** - Same interface, better performance

## Testing

Run the transport optimizer to test:
```bash
python main.py
# Option 2: Optimize transport route
# Try: "Eiffel Tower to Louvre"
```

Expected behavior:
- Tool calls appear IMMEDIATELY as: 📍 Searching for location...
- AI response streams token by token
- All functionality (route collection, transport options, cost calculation, PDF generation) works as before
