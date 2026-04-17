"""
Main CLI entry point for the Itinerary Document Generator and Transport Optimizer.

This is a multi-agent LangGraph system with two main features:

1. Itinerary Generator - Creates travel itinerary documents
   - Day Organizer: organizes attractions by days using K-means clustering
   - Attraction Researcher: researches details for each attraction (parallel execution)

2. Transport Optimizer - Optimizes city transport routes
   - Route Collector: gathers route pairs from user conversation
   - Transport Researcher: researches transport options and collects preferences
   - Cost Calculator: calculates costs and generates PDF summary
"""
import asyncio
import os
import sys
from uuid import uuid4
from dotenv import load_dotenv
from colorama import Fore, Style
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from langgraph.types import Command
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from src.itinerary_generator.graph import build_graph
from src.processor.email_processor import check_email_config, send_itinerary_email_sync
from src.utils.observability import setup_langsmith_tracing

# Load environment variables
load_dotenv()

# Setup LangSmith tracing (if configured)
tracing_enabled = setup_langsmith_tracing()

# Initialize Rich console
console = Console()

# Supported languages
SUPPORTED_LANGUAGES = {
    "en": "English",
    "pt-br": "Portuguese (Brazil)",
    "es": "Spanish",
    "fr": "French",
}

# Friendly tool messages
TOOL_MESSAGES = {
    "search_place_coordinates": "📍 Searching for location...",
    "register_route_pair": "✅ Registering route...",
    "confirm_route_pairs": "📋 Confirming routes...",
    "get_transport_options": "🚇 Checking transport options...",
    "register_user_preference": "💾 Saving your preference...",
    "finish_transport_research": "✨ Finishing transport research...",
    "search_transport_information": "🔎 Researching transport prices...",
    "route_reasoning": "🤔 Analyzing route...",
    "register_route_cost": "💰 Registering cost...",
    "register_payment_methods": "💳 Saving payment methods...",
    "finish_interaction": "📄 Generating PDF...",
}


def check_environment():
    """Check if required environment variables are set."""
    issues = []

    # Check LLM API key
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("OPENROUTER_API_KEY"):
        issues.append("No LLM API key configured (OPENAI_API_KEY, ANTHROPIC_API_KEY, or OPENROUTER_API_KEY)")
    else:
        if os.getenv("ANTHROPIC_API_KEY"):
            console.print("Anthropic API configured", style="green")
        if os.getenv("OPENAI_API_KEY"):
            console.print("OpenAI API configured", style="green")
        if os.getenv("OPENROUTER_API_KEY"):
            console.print("OpenRouter API configured", style="green")

    # Check Serper (required for place address search)
    if not os.getenv("SERPER_API_KEY"):
        issues.append("SERPER_API_KEY not configured (required for place address search)")
    else:
        console.print("Serper configured (Google Places search)", style="green")

    # Check Tavily (required for web search and images)
    if not os.getenv("TAVILY_API_KEY"):
        issues.append("TAVILY_API_KEY not configured (required for web search and images)")
    else:
        console.print("Tavily configured (web search + images)", style="green")

    # Check LangSmith tracing
    if tracing_enabled:
        project = os.getenv("LANGSMITH_PROJECT", "itinerary-generator")
        console.print(f"LangSmith tracing enabled (project: {project})", style="green")
    else:
        console.print("[dim]LangSmith tracing disabled (optional)[/dim]")

    if issues:
        console.print("\n[bold yellow]Configuration Warnings:[/bold yellow]")
        for issue in issues:
            console.print(f"  {issue}")

        console.print("\n[dim]Configure the keys in the .env file[/dim]")
        console.print("[dim]Required: SERPER_API_KEY (for place search) and TAVILY_API_KEY (for web search)[/dim]\n")

        if any("No LLM API key" in issue for issue in issues):
            console.print("[bold red]Cannot continue without configuring at least one LLM.[/bold red]")
            return False

    return True


def get_attractions_input() -> str:
    """Get attractions list from user."""
    console.print("\n[bold cyan]List the attractions you want to visit:[/bold cyan]")
    console.print("[dim]You can list in any format.[/dim]")
    console.print()
    console.print("[dim]Example:[/dim]")
    console.print("[dim]   - Eiffel Tower and surroundings (climb, trocadero, photo streets)[/dim]")
    console.print("[dim]   - Louvre Museum[/dim]")
    console.print("[dim]   - Palace of Versailles[/dim]")
    console.print()
    console.print("[dim]Type 'END' on a separate line when finished.[/dim]\n")

    lines = []
    while True:
        try:
            line = input()
            if line.strip().upper() == "END":
                break
            lines.append(line)
        except EOFError:
            break

    return "\n".join(lines).strip()


def get_preferences_input() -> str:
    """Get user preferences including age, organization preferences, etc."""
    console.print("\n[bold cyan]Preferences (optional):[/bold cyan]")
    console.print("[dim]Can include: age, day organization preferences, etc.[/dim]")
    console.print()
    console.print("[dim]Example:[/dim]")
    console.print("[dim]   'I'm 25 years old. On the first day I prefer museums.'[/dim]")
    console.print()
    console.print("[dim]Type 'END' on a separate line when finished (or leave empty and type END).[/dim]\n")

    lines = []
    while True:
        try:
            line = input()
            if line.strip().upper() == "END":
                break
            lines.append(line)
        except EOFError:
            break

    return "\n".join(lines).strip()


def get_num_days() -> int:
    """Get number of days for the itinerary."""
    while True:
        try:
            days = Prompt.ask("\n[bold cyan]How many days for the itinerary?[/bold cyan]", default="3")
            number = int(days)
            if number > 0:
                return number
            else:
                console.print("[yellow]Please enter a positive number.[/yellow]")
        except ValueError:
            console.print("[yellow]Please enter a valid number.[/yellow]")


def get_language() -> str:
    """Get desired language for the output document."""
    console.print("\n[bold cyan]Select the output language for the document:[/bold cyan]")
    for code, name in SUPPORTED_LANGUAGES.items():
        console.print(f"  {code}: {name}")

    while True:
        lang = Prompt.ask(
            "\n[bold cyan]Language code[/bold cyan]",
            default="en",
            choices=list(SUPPORTED_LANGUAGES.keys())
        )
        if lang in SUPPORTED_LANGUAGES:
            console.print(f"[dim]Selected: {SUPPORTED_LANGUAGES[lang]}[/dim]")
            return lang
        console.print("[yellow]Please select a valid language code.[/yellow]")


def check_transport_optimizer_env():
    """Check if transport optimizer environment is configured."""
    issues = []

    # Check Google Maps API
    if not os.getenv("GOOGLE_MAPS_API_KEY"):
        issues.append("GOOGLE_MAPS_API_KEY not configured (required for transport directions)")
    else:
        console.print("Google Maps API configured", style="green")

    # Check Serper (required for pricing research)
    if not os.getenv("SERPER_API_KEY"):
        issues.append("SERPER_API_KEY not configured (required for pricing research)")

    # Check LLM API
    if not os.getenv("OPENROUTER_API_KEY"):
        issues.append("OPENROUTER_API_KEY not configured (required for agent LLM)")

    if issues:
        console.print("\n[bold yellow]Transport Optimizer Configuration Issues:[/bold yellow]")
        for issue in issues:
            console.print(f"  {issue}")
        return False

    return True


def run_transport_optimizer():
    """Run the transport optimizer chat interface."""
    console.print("\n" + "="*60)
    console.print("[bold bright_blue]Mode: Transport Optimizer[/bold bright_blue]")
    console.print("="*60)

    # Check environment
    if not check_transport_optimizer_env():
        console.print("\n[yellow]Transport optimizer is not fully configured.[/yellow]")
        console.print("[dim]Add the missing API keys to your .env file.[/dim]\n")
        return

    # Get output language
    console.print("\n[bold cyan]Select the output language:[/bold cyan]")
    for code, name in SUPPORTED_LANGUAGES.items():
        console.print(f"  {code}: {name}")

    language = Prompt.ask(
        "\n[bold cyan]Language code[/bold cyan]",
        default="en",
        choices=list(SUPPORTED_LANGUAGES.keys())
    )

    try:
        # Import and build graph
        from src.transport_optimizer.graph import build_transport_optimizer_graph, get_initial_state

        console.print("\n[dim]Initializing transport optimizer...[/dim]")
        checkpointer = MemorySaver()
        graph = build_transport_optimizer_graph(checkpointer=checkpointer)

        console.print("Transport optimizer ready!\n", style="green")
        console.print("[dim]Agents:[/dim]")
        console.print("[dim]  -> Route Collector: Gathers your route pairs[/dim]")
        console.print("[dim]  -> Transport Researcher: Finds transport options[/dim]")
        console.print("[dim]  -> Cost Calculator: Calculates costs and generates PDF[/dim]\n")

        # Initialize state
        config = {
            "configurable": {"thread_id": str(uuid4())},
            "recursion_limit": 100,
        }

        initial_state = get_initial_state(language=language)

        console.print("[bold cyan]Transport Optimizer[/bold cyan]")
        console.print("[dim]Tell me about your route. Example: 'I want to go from Eiffel Tower to Louvre, then to Notre Dame'[/dim]")
        console.print("[dim]Type 'quit' to exit.[/dim]\n")

        # Chat loop
        current_state = initial_state
        seen_content = set()

        while True:
            try:
                # Ask for input when: no messages yet (first iteration) OR agent expects it (next_agent == "end")
                has_messages = bool(current_state.get("messages"))
                waiting_for_input = current_state.get("next_agent", "end") == "end"

                if not has_messages or waiting_for_input:
                    user_input = Prompt.ask("\n\n[bold green]You[/bold green]")

                    if user_input.lower().strip() in ['quit', 'exit', 'q']:
                        console.print("\n[bold green]Goodbye! Have a great trip![/bold green]")
                        break

                    if not user_input.strip():
                        continue

                    # Add user message to state
                    current_state["messages"] = current_state.get("messages", []) + [
                        HumanMessage(content=user_input)
                    ]
                    console.print()

                # Stream the graph with real-time events
                async def _process_stream():
                    nonlocal current_state

                    # Track state for streaming
                    summarization_model_runs = set()  # Track model run_ids that are summarization
                    content_buffers = {}  # Buffer content by run_id: {run_id: {"content": str, "has_tools": bool}}

                    async for event in graph.astream_events(current_state, config=config, version="v2"):
                        event_type = event.get("event", "")
                        event_name = event.get("name", "")
                        event_data = event.get("data", {})
                        event_metadata = event.get("metadata", {})
                        run_id = event.get("run_id", "")

                        # Tool start event - show friendly message EVERY TIME
                        if event_type == "on_tool_start":
                            tool_name = event_name
                            if tool_name:
                                friendly_msg = TOOL_MESSAGES.get(tool_name, f"🔧 {tool_name}...")
                                console.print(f"\n[dim]{friendly_msg}[/dim]")

                        # Chat model start - detect if this is summarization
                        elif event_type == "on_chat_model_start":
                            input_data = event_data.get("input", {})
                            input_str = str(input_data)
                            if "Summarize this transport planning conversation" in input_str or "Previous Conversation Summary" in input_str:
                                summarization_model_runs.add(run_id)

                        # Chat model streaming - only stream if no tool calls
                        elif event_type == "on_chat_model_stream":
                            # Skip if this is a summarization model call
                            if run_id in summarization_model_runs:
                                continue

                            chunk = event_data.get("chunk")
                            if chunk:
                                # Initialize tracking for this run_id if needed
                                if run_id not in content_buffers:
                                    content_buffers[run_id] = {"content": "", "has_tools": False, "started_printing": False}

                                # Check for tool_calls in chunk
                                if hasattr(chunk, "tool_call_chunks") and chunk.tool_call_chunks:
                                    content_buffers[run_id]["has_tools"] = True

                                # Stream text content immediately ONLY if no tool calls
                                if hasattr(chunk, "content") and chunk.content and isinstance(chunk.content, str):
                                    if not content_buffers[run_id]["has_tools"]:
                                        if not content_buffers[run_id]["started_printing"]:
                                            content_buffers[run_id]["started_printing"] = True
                                            print(f"\n{Fore.CYAN}", end="", flush=True)
                                        print(chunk.content, end="", flush=True)

                                    # Still accumulate for reference
                                    content_buffers[run_id]["content"] += chunk.content

                        # Chat model end - close streams properly
                        elif event_type == "on_chat_model_end":
                            if run_id in summarization_model_runs:
                                summarization_model_runs.discard(run_id)
                                continue

                            # Finish the streamed content (add newline and reset color)
                            if run_id in content_buffers:
                                buffer = content_buffers[run_id]
                                if buffer.get("started_printing"):
                                    print(f"{Style.RESET_ALL}\n", flush=True)
                                del content_buffers[run_id]

                        # Chain end event - capture final state from graph level
                        elif event_type == "on_chain_end":
                            langgraph_node = event_metadata.get("langgraph_node")

                            # Capture state updates from node outputs
                            output = event_data.get("output")
                            if isinstance(output, dict) and langgraph_node:
                                current_state.update(output)

                                # Check if interaction is complete
                                if output.get("interaction_complete"):
                                    pdf_path = output.get("final_pdf_path", "")
                                    if pdf_path:
                                        console.print(f"\n[bold green]PDF generated:[/bold green] {pdf_path}")
                                    console.print("\n[bold green]Transport optimization complete![/bold green]")
                                    return

                # Run async stream in sync context
                asyncio.run(_process_stream())

                # Check if interaction is complete and exit the loop
                if current_state.get("interaction_complete"):
                    break

                # Loop continues automatically if next_agent != "end"
                # (no user input needed for agent-to-agent transitions)

            except KeyboardInterrupt:
                console.print("\n[yellow]Interrupted.[/yellow]")
                break
            except Exception as e:
                console.print(f"[bold red]Error: {e}[/bold red]")
                import traceback
                traceback.print_exc()

    except ImportError as e:
        console.print(f"[bold red]Error importing transport optimizer: {e}[/bold red]")
        console.print("[dim]Make sure all dependencies are installed.[/dim]")
    except Exception as e:
        console.print(f"[bold red]Error initializing transport optimizer: {e}[/bold red]")
        import traceback
        traceback.print_exc()


def main():
    """Main CLI function."""

    # Check environment
    if not check_environment():
        sys.exit(1)

    console.print()

    # Initialize graph
    try:
        console.print("[dim]Initializing multi-agent system...[/dim]")
        graph = build_graph()

        console.print("Multi-agent system initialized successfully!\n", style="green")
        console.print("[dim]  -> Agent 1: Day Organizer (uses geographic distance)[/dim]")
        console.print("[dim]  -> Agent 2: Attraction Researcher (parallel execution)[/dim]\n")

    except Exception as e:
        console.print(f"[bold red]Error initializing system: {e}[/bold red]")
        sys.exit(1)

    # Main interaction loop
    while True:
        console.print("[bold]Choose an option:[/bold]")
        console.print("1. Generate travel itinerary")
        console.print("2. Optimize transport route")
        console.print("3. Exit")

        option = Prompt.ask("\nOption", choices=["1", "2", "3"], default="1")

        if option == "3":
            console.print("\n[bold green]Goodbye! Have a great trip![/bold green]")
            break

        elif option == "2":
            # Transport optimizer mode
            run_transport_optimizer()

        elif option == "1":
            # Generate itinerary mode
            console.print("\n" + "="*60)
            console.print("[bold bright_blue]Mode: Day-by-Day Itinerary Generation[/bold bright_blue]")
            console.print("="*60)

            # Get attractions list
            attractions_input = get_attractions_input()

            if not attractions_input.strip():
                console.print("[yellow]No information provided. Please try again.[/yellow]\n")
                continue

            # Get preferences (optional)
            preferences_input = get_preferences_input()

            # Get number of days
            num_days = get_num_days()

            # Get output language
            language = get_language()

            # Generate itinerary using graph
            console.print("\n[bold yellow]Generating itinerary with multi-agent system... This may take a few minutes.[/bold yellow]")
            console.print("[dim]Steps:[/dim]")
            console.print("[dim]  1. Agent 1: Organize attractions by day (based on preferences or distance)[/dim]")
            console.print("[dim]  2. Agent 2: Research each attraction in parallel (info + images)[/dim]")
            console.print("[dim]  3. Generate formatted DOCX document[/dim]\n")

            try:
                # Initialize graph state
                initial_state = {
                    "user_input": attractions_input,
                    "num_days": num_days,
                    "preferences_input": preferences_input,
                    "language": language,
                    "document_title": "",
                    "attractions_by_day": [],
                    "processed_attractions": [],
                    "clusters": [],
                    "attraction_coordinates": {},
                    "final_document_path": "",
                    "costs_by_currency": {},
                    "invalid_input": False,
                    "error_message": "",
                    "organized_days": {},
                    "has_flexible_attractions": False,
                    "itinerary_approved": False,
                    "user_feedback": "",
                    "api_mode": False,
                    "failed_coordinate_lookups": [],
                }

                config = {
                    "recursion_limit": 1000,
                }

                # Invoke graph
                console.print("[dim]Executing multi-agent workflow...[/dim]\n")
                final_state = graph.invoke(initial_state, config=config)

                # Display result
                console.print("\n" + "="*60)
                if final_state.get("invalid_input"):
                    # Input was invalid - show error message
                    error_message = final_state.get("error_message", "Invalid input.")
                    console.print("[bold yellow]Could not generate itinerary[/bold yellow]")
                    console.print("="*60)
                    console.print(f"\n{error_message}\n")
                elif final_state.get("final_document_path"):
                    document_path = final_state['final_document_path']
                    console.print(f"[bold green]{num_days}-day itinerary generated successfully![/bold green]")
                    console.print("="*60)
                    console.print(f"\n[bold]File:[/bold] {document_path}")

                    # Show cost summary if available
                    costs = final_state.get("costs_by_currency", {})
                    if costs:
                        console.print("\n[bold]Estimated costs (per person):[/bold]")
                        for currency, total in costs.items():
                            console.print(f"  {currency}: {total:.2f}")

                    # Offer to send via email
                    console.print()
                    send_email = Confirm.ask(
                        "[bold cyan]Would you like to send the itinerary via email?[/bold cyan]",
                        default=False
                    )

                    if send_email:
                        # Check email configuration
                        email_config = check_email_config()

                        if not email_config["configured"]:
                            console.print("\n[yellow]Email not configured.[/yellow]")
                            console.print(f"[dim]{email_config['message']}[/dim]")
                            if email_config.get("help"):
                                console.print(f"[dim]{email_config['help']}[/dim]")
                        else:
                            # Get recipient email(s)
                            console.print("[dim]Tip: Separate multiple emails with commas[/dim]")
                            recipient = Prompt.ask(
                                "\n[bold cyan]Recipient email address(es)[/bold cyan]",
                                default="",
                            )

                            # Validate at least one valid email
                            emails = [e.strip() for e in recipient.split(",") if e.strip() and "@" in e.strip()]
                            if emails:
                                # Extract destination from document title or user input
                                destination = final_state.get("document_title", "")
                                if not destination:
                                    destination = attractions_input.split("\n")[0][:30]

                                console.print(f"\n[dim]Sending to {', '.join(emails)}...[/dim]")

                                result = send_itinerary_email_sync(
                                    document_path=document_path,
                                    to_emails=emails,
                                    destination=destination,
                                    num_days=num_days,
                                    language=language,
                                )

                                if result.get("success"):
                                    num_recipients = len(result.get("recipients", emails))
                                    if num_recipients > 1:
                                        console.print(f"[bold green]Email sent successfully to {num_recipients} recipients![/bold green]")
                                    else:
                                        console.print("[bold green]Email sent successfully![/bold green]")
                                else:
                                    console.print(f"[bold red]Failed to send email: {result.get('error')}[/bold red]")
                                    if result.get("help"):
                                        console.print(f"[dim]{result['help']}[/dim]")
                            else:
                                console.print("[yellow]No valid email address provided.[/yellow]")
                else:
                    console.print("[bold yellow]Itinerary processed but document was not generated[/bold yellow]")
                    console.print("="*60)
                console.print()

            except Exception as e:
                console.print(f"\n[bold red]Error generating itinerary: {e}[/bold red]\n")
                import traceback
                traceback.print_exc()

        else:
            console.print("[yellow]Invalid option. Please try again.[/yellow]\n")

        console.print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n\n[bold yellow]Program interrupted by user.[/bold yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]Fatal error: {e}[/bold red]")
        sys.exit(1)
