# LangChain 1.0 Compatibility Notes

This project is built with **LangChain 1.0** (stable release, October 2025) and follows all v1.0 requirements and best practices.

## Version Requirements

```txt
langchain>=1.0.0
langchain-core>=1.0.0
langchain-openai>=1.0.0
langchain-anthropic>=0.3.0
langgraph>=0.2.0
python>=3.10
```

## LangChain 1.0 Compliance

### ✅ What We Did Right

#### 1. TypedDict State Schema (Required)
**V1.0 Requirement**: Agent state must use `TypedDict`, not Pydantic models or dataclasses.

```python
# ✅ CORRECT (what we use)
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    """State using TypedDict as required by v1.0"""
    messages: Annotated[list, add_messages]

# ❌ WRONG (deprecated in v1.0)
from pydantic import BaseModel

class AgentState(BaseModel):  # Not supported in v1.0!
    messages: list
```

**Location**: `agent/graph.py` lines 20-27

#### 2. Custom Graph Implementation
**V1.0 Change**: `create_react_agent` moved from `langgraph.prebuilt` to `langchain.agents.create_agent`

We **don't use** the prebuilt agent creator. Instead, we built a custom graph, which means:
- ✅ No import path changes needed
- ✅ Full control over agent behavior
- ✅ No migration required

**Location**: `agent/graph.py` lines 56-103

#### 3. Python 3.10+ Support
**V1.0 Requirement**: Python 3.9 dropped (reached EOL October 2025)

```python
# Our requirements
python>=3.10  # ✅ Compliant
```

#### 4. Tool Definitions
**V1.0 Compatible**: Using `@tool` decorator from `langchain_core.tools`

```python
from langchain_core.tools import tool

@tool
def search_flights(origin: str, destination: str, date: str) -> str:
    """Tool description for LLM."""
    # Implementation
    return json.dumps(results)
```

**Location**: `agent/tools.py`

#### 5. Message Types
**V1.0 Update**: Return type for chat models fixed to `AIMessage` (was `BaseMessage`)

```python
# ✅ We correctly use AIMessage type hints
from langchain_core.messages import AIMessage

if isinstance(message, AIMessage):
    return message.content
```

**Location**: `agent/graph.py` lines 128-129

### 🔄 Breaking Changes from 0.3 to 1.0

#### Changes That DON'T Affect Us

1. **`create_react_agent` import change**
   - Old: `from langgraph.prebuilt import create_react_agent`
   - New: `from langchain.agents import create_agent`
   - **Impact**: None (we don't use it)

2. **Parameter renames in `create_agent`**
   - `prompt` → `system_prompt`
   - **Impact**: None (we don't use it)

3. **Legacy chains removed**
   - ConversationalChain, ConstitutionalChain, etc.
   - **Impact**: None (we use modern LangGraph)

4. **Pydantic models for state**
   - No longer supported
   - **Impact**: None (we use TypedDict)

#### Changes We Implemented

1. **Python 3.10+ Required** ✅
   - Specified in documentation
   - Updated requirements

2. **TypedDict for State** ✅
   - Already implemented from the start

3. **Proper Type Hints** ✅
   - Using `AIMessage` not `BaseMessage`

## What Makes This v1.0 Compliant

### Code Structure

```python
# agent/graph.py - Fully v1.0 compliant

# 1. TypedDict state (v1.0 requirement)
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

# 2. Custom graph (no deprecated imports)
def _build_graph(self):
    workflow = StateGraph(AgentState)

    # 3. Manual tool binding (v1.0 compatible)
    def agent_node(state: AgentState):
        llm_with_tools = self.llm.bind_tools(ALL_TOOLS)
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    # 4. Modern graph construction
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode(ALL_TOOLS))
    workflow.add_conditional_edges("agent", tools_condition)
    workflow.add_edge("tools", "agent")

    return workflow.compile()
```

### Dependencies

```txt
# requirements.txt - All v1.0 compatible

langchain>=1.0.0           # Main package (v1.0 stable)
langchain-core>=1.0.0      # Core abstractions (v1.0 stable)
langchain-openai>=1.0.0    # OpenAI integration (v1.0 stable)
langchain-anthropic>=0.3.0 # Anthropic integration
langgraph>=0.2.0           # Graph orchestration
```

## Migration from 0.3 → 1.0

If you were using LangChain 0.3, here's what changed:

### Before (0.3):
```python
# Old requirements
langchain>=0.3.0
langchain-core>=0.3.0

# Could use Pydantic models
class AgentState(BaseModel):
    messages: list

# Used old import
from langgraph.prebuilt import create_react_agent
```

### After (1.0):
```python
# New requirements
langchain>=1.0.0
langchain-core>=1.0.0

# Must use TypedDict
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

# Updated import (if using prebuilt)
from langchain.agents import create_agent
```

## Why Our Implementation Was Already Compatible

We followed best practices from the beginning:

1. **Used TypedDict** - Even though 0.3 allowed Pydantic, we chose TypedDict
2. **Built custom graph** - Didn't rely on deprecated helpers
3. **Modern patterns** - Used latest LangGraph features
4. **Python 3.10** - Already specified in docs

This means **zero breaking changes** for our codebase when upgrading to 1.0!

## Testing v1.0 Compatibility

Run the test suite to verify everything works:

```bash
# Install v1.0
pip install --upgrade langchain>=1.0.0 langchain-core>=1.0.0

# Run tests
python test_agent.py

# Should see:
# ✓ All imports successful
# ✓ Agent initialized
# ✓ Tools loaded
```

## Key Differences from v0.3

### 1. State Schemas
| v0.3 | v1.0 |
|------|------|
| Pydantic allowed | TypedDict only |
| Dataclasses allowed | TypedDict only |
| TypedDict allowed | TypedDict required |

### 2. Agent Creation
| v0.3 | v1.0 |
|------|------|
| `langgraph.prebuilt` | `langchain.agents` |
| `create_react_agent` | `create_agent` |
| `prompt` parameter | `system_prompt` parameter |

### 3. Python Support
| v0.3 | v1.0 |
|------|------|
| Python 3.8+ | Python 3.10+ |
| Pydantic 1 & 2 | Pydantic 2 only |

### 4. Legacy Chains
| v0.3 | v1.0 |
|------|------|
| Still in main package | Moved to `langchain-classic` |
| Import from `langchain.chains` | Install separately |

## What We Use from v1.0

### Core Features:
- ✅ `StateGraph` - Graph construction
- ✅ `TypedDict` - State definition
- ✅ `@tool` - Tool decorator
- ✅ `bind_tools()` - Tool binding
- ✅ `ToolNode` - Tool execution
- ✅ `tools_condition` - Conditional routing

### Integrations:
- ✅ `ChatOpenAI` - OpenAI models
- ✅ `ChatAnthropic` - Anthropic models
- ✅ Message types - `HumanMessage`, `AIMessage`, `SystemMessage`

## Benefits of v1.0

1. **More stable API** - Breaking changes complete
2. **Better type safety** - TypedDict enforcement
3. **Cleaner imports** - Consolidated structure
4. **Improved performance** - Optimizations
5. **Better documentation** - Official migration guides

## References

- [LangChain v1 Migration Guide](https://docs.langchain.com/oss/python/migrate/langchain-v1)
- [LangChain 1.0 Release Announcement](https://blog.langchain.com/langchain-langchain-1-0-alpha-releases/)
- [LangChain Release Policy](https://python.langchain.com/docs/versions/release_policy/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)

## Summary

✅ **This project is fully LangChain 1.0 compliant**

- Uses TypedDict state schemas (required)
- Python 3.10+ support (required)
- No deprecated imports
- Follows v1.0 best practices
- Zero migration needed from our 0.3 implementation

The code was written with v1.0 patterns from the start, making it forward-compatible and production-ready!
