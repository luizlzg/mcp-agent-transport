"""Main entry point for the European Transportation AI Agent."""
import os
import sys
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from agent.graph import TransportationAgent
from agent.prompts import WELCOME_MESSAGE

# Load environment variables
load_dotenv()

# Initialize rich console for beautiful output
console = Console()


def print_welcome():
    """Print welcome message."""
    welcome_panel = Panel(
        Markdown(WELCOME_MESSAGE),
        title="European Transport Assistant",
        border_style="blue"
    )
    console.print(welcome_panel)


def check_api_keys():
    """Check which API keys are configured and provide setup instructions."""
    keys_status = []

    # LLM Provider
    if os.getenv("OPENAI_API_KEY"):
        keys_status.append("✓ OpenAI API Key configured")
        llm_configured = True
    elif os.getenv("ANTHROPIC_API_KEY"):
        keys_status.append("✓ Anthropic API Key configured")
        llm_configured = True
    else:
        keys_status.append("✗ No LLM API key found (set OPENAI_API_KEY or ANTHROPIC_API_KEY)")
        llm_configured = False

    # Transportation APIs
    if os.getenv("AMADEUS_API_KEY") and os.getenv("AMADEUS_API_SECRET"):
        keys_status.append("✓ Amadeus API configured (Flights)")
    else:
        keys_status.append("✗ Amadeus API not configured (Flights will be limited)")

    if os.getenv("SNCF_API_KEY"):
        keys_status.append("✓ SNCF API configured (Trains)")
    else:
        keys_status.append("✗ SNCF API not configured (Train search limited)")

    if os.getenv("RAPIDAPI_KEY"):
        keys_status.append("✓ RapidAPI configured (FlixBus)")
    else:
        keys_status.append("✗ RapidAPI not configured (Bus search limited)")

    # Print status
    console.print("\n[bold]API Configuration Status:[/bold]")
    for status in keys_status:
        if "✓" in status:
            console.print(f"  [green]{status}[/green]")
        else:
            console.print(f"  [yellow]{status}[/yellow]")

    console.print()

    if not llm_configured:
        console.print("[red bold]ERROR: No LLM API key configured![/red bold]")
        console.print("\nPlease set one of the following in your .env file:")
        console.print("  - OPENAI_API_KEY=your_key")
        console.print("  - ANTHROPIC_API_KEY=your_key")
        console.print("\nSee .env.example for a template.")
        return False

    return True


def get_agent():
    """Initialize and return the agent based on available API keys."""
    if os.getenv("OPENAI_API_KEY"):
        console.print("[dim]Using OpenAI GPT-4...[/dim]\n")
        return TransportationAgent(
            model_provider="openai",
            model_name="gpt-4"
        )
    elif os.getenv("ANTHROPIC_API_KEY"):
        console.print("[dim]Using Anthropic Claude...[/dim]\n")
        return TransportationAgent(
            model_provider="anthropic",
            model_name="claude-sonnet-4-5-20250929"
        )
    else:
        raise ValueError("No LLM API key configured")


def interactive_chat():
    """Run the interactive chat interface."""
    print_welcome()

    # Check API configuration
    if not check_api_keys():
        return

    # Initialize agent
    try:
        agent = get_agent()
    except Exception as e:
        console.print(f"[red]Error initializing agent: {e}[/red]")
        return

    # Chat loop
    console.print("[bold cyan]Chat started![/bold cyan] Type 'quit' or 'exit' to end.\n")

    thread_id = "main_session"

    while True:
        try:
            # Get user input
            user_input = Prompt.ask("\n[bold green]You[/bold green]")

            # Check for exit commands
            if user_input.lower() in ["quit", "exit", "bye"]:
                console.print("\n[cyan]Thank you for using European Transport Assistant! Safe travels![/cyan]")
                break

            # Check for empty input
            if not user_input.strip():
                continue

            # Show thinking indicator
            console.print("[dim]Thinking...[/dim]")

            # Get agent response
            try:
                response = agent.chat(user_input, thread_id=thread_id)

                # Display response
                console.print(f"\n[bold blue]Agent:[/bold blue]")
                console.print(Markdown(response))

            except Exception as e:
                console.print(f"\n[red]Error getting response: {e}[/red]")
                console.print("[yellow]Please try again.[/yellow]")

        except KeyboardInterrupt:
            console.print("\n\n[cyan]Chat interrupted. Goodbye![/cyan]")
            break
        except EOFError:
            console.print("\n\n[cyan]Goodbye![/cyan]")
            break


def main():
    """Main entry point."""
    try:
        interactive_chat()
    except Exception as e:
        console.print(f"\n[red bold]Fatal error: {e}[/red bold]")
        import traceback
        console.print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
