"""
LangGraph ReAct agent for transportation search.

Built with LangChain 1.0:
- Uses TypedDict for state (v1.0 requirement)
- Compatible with langchain>=1.0.0, langchain-core>=1.0.0
- Follows LangChain 1.0 patterns and best practices
- Includes MemorySaver for conversation persistence
"""
from typing import Annotated, Literal, TypedDict
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from agent.tools import ALL_TOOLS
from agent.prompts import SYSTEM_PROMPT
import os


class AgentState(TypedDict):
    """
    State for the transportation agent.

    Using TypedDict as required by LangChain 1.0
    (Pydantic models and dataclasses no longer supported)
    """
    messages: Annotated[list, add_messages]


class TransportationAgent:
    """
    ReAct agent for finding European transportation routes.

    Built with LangChain 1.0 and LangGraph:
    - Uses TypedDict state schema (v1.0 compliant)
    - Custom graph implementation (not using deprecated create_react_agent)
    - Compatible with langchain>=1.0.0, langchain-core>=1.0.0
    - Requires Python 3.10+ (v1.0 requirement)
    """

    def __init__(self, model_provider: str = "anthropic", model_name: str = "gpt-4"):
        """
        Initialize the transportation agent.

        Args:
            model_provider: LLM provider ('openai' or 'anthropic')
            model_name: Model name to use
        """
        self.model_provider = model_provider
        self.model_name = model_name
        self.llm = self._initialize_llm()
        # Initialize memory checkpointer for conversation persistence
        self.memory = MemorySaver()
        self.graph = self._build_graph()

    def _initialize_llm(self):
        """Initialize the LLM based on provider."""
        if self.model_provider == "openai":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=self.model_name,
                temperature=0,
                streaming=True
            )
        elif self.model_provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model=self.model_name,
                temperature=0,
                streaming=True
            )
        else:
            raise ValueError(f"Unsupported model provider: {self.model_provider}")

    def _build_graph(self):
        """Build the LangGraph ReAct agent."""
        # Create the agent node
        def agent_node(state: AgentState):
            """Agent reasoning node."""
            # Bind tools to the LLM
            llm_with_tools = self.llm.bind_tools(ALL_TOOLS)

            # Get messages from state
            messages = state["messages"]

            # Add system message if not present
            if not any(isinstance(m, SystemMessage) for m in messages):
                messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages

            # Invoke the LLM
            response = llm_with_tools.invoke(messages)

            return {"messages": [response]}

        # Create tool node
        tool_node = ToolNode(ALL_TOOLS)

        # Build the graph
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("agent", agent_node)
        workflow.add_node("tools", tool_node)

        # Add edges
        workflow.add_edge(START, "agent")

        # Conditional edge: if agent calls tools, go to tools node, otherwise end
        workflow.add_conditional_edges(
            "agent",
            tools_condition,
            {
                "tools": "tools",
                END: END
            }
        )

        # After tools, go back to agent
        workflow.add_edge("tools", "agent")

        # Compile the graph with memory checkpointer for conversation persistence
        return workflow.compile(checkpointer=self.memory)

    def chat(self, message: str, thread_id: str = "default") -> str:
        """
        Send a message to the agent and get a response.

        Args:
            message: User message
            thread_id: Thread ID for conversation tracking

        Returns:
            Agent's response
        """
        # Create config with thread_id for conversation memory
        config = {"configurable": {"thread_id": thread_id}}

        # Invoke the graph
        result = self.graph.invoke(
            {"messages": [HumanMessage(content=message)]},
            config=config
        )

        # Extract the last AI message
        messages = result["messages"]
        for message in reversed(messages):
            if isinstance(message, AIMessage):
                content = message.content
                # Handle content that might be a list or string
                if isinstance(content, list):
                    # Join list items or extract text from content blocks
                    return " ".join(str(item) if not isinstance(item, dict) else item.get("text", str(item)) for item in content)
                return content

        return "No response generated."

    def stream_chat(self, message: str, thread_id: str = "default"):
        """
        Stream a conversation with the agent.

        Args:
            message: User message
            thread_id: Thread ID for conversation tracking

        Yields:
            Chunks of the agent's response
        """
        config = {"configurable": {"thread_id": thread_id}}

        # Stream the graph execution
        for event in self.graph.stream(
            {"messages": [HumanMessage(content=message)]},
            config=config,
            stream_mode="values"
        ):
            # Get the last message
            if "messages" in event and event["messages"]:
                last_message = event["messages"][-1]

                if isinstance(last_message, AIMessage):
                    yield last_message.content


# Example usage
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()

    # Check which provider is available
    if os.getenv("OPENAI_API_KEY"):
        agent = TransportationAgent(model_provider="anthropic", model_name="gpt-4")
    elif os.getenv("ANTHROPIC_API_KEY"):
        agent = TransportationAgent(
            model_provider="anthropic",
            model_name="claude-4-5-sonnet"
        )
    else:
        print("Please set OPENAI_API_KEY or ANTHROPIC_API_KEY in .env file")
        exit(1)

    # Test the agent
    print("Agent: Hello! I can help you find transportation between European cities.")
    print()

    response = agent.chat(
        "I need to travel from Paris to Berlin on 2025-11-15. What are my options?"
    )

    print(f"Agent: {response}")
