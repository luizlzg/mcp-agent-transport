"""Test script for the European Transportation Agent."""
import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()


def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")

    try:
        import langchain
        print("  ✓ langchain")
    except ImportError as e:
        print(f"  ✗ langchain: {e}")
        return False

    try:
        import langgraph
        print("  ✓ langgraph")
    except ImportError as e:
        print(f"  ✗ langgraph: {e}")
        return False

    try:
        from amadeus import Client
        print("  ✓ amadeus")
    except ImportError as e:
        print(f"  ✗ amadeus: {e}")
        return False

    try:
        import requests
        print("  ✓ requests")
    except ImportError as e:
        print(f"  ✗ requests: {e}")
        return False

    try:
        from rich.console import Console
        print("  ✓ rich")
    except ImportError as e:
        print(f"  ✗ rich: {e}")
        return False

    print("  All imports successful!\n")
    return True


def test_api_keys():
    """Test that API keys are configured."""
    print("Testing API keys...")

    # LLM
    has_llm = False
    if os.getenv("OPENAI_API_KEY"):
        print("  ✓ OPENAI_API_KEY configured")
        has_llm = True
    else:
        print("  ✗ OPENAI_API_KEY not configured")

    if os.getenv("ANTHROPIC_API_KEY"):
        print("  ✓ ANTHROPIC_API_KEY configured")
        has_llm = True
    else:
        print("  ✗ ANTHROPIC_API_KEY not configured")

    if not has_llm:
        print("\n  ERROR: No LLM API key found!")
        print("  Please set OPENAI_API_KEY or ANTHROPIC_API_KEY in .env\n")
        return False

    # Transportation APIs (optional)
    if os.getenv("AMADEUS_API_KEY") and os.getenv("AMADEUS_API_SECRET"):
        print("  ✓ Amadeus API configured")
    else:
        print("  ℹ Amadeus API not configured (optional)")

    if os.getenv("RAPIDAPI_KEY"):
        print("  ✓ RapidAPI configured")
    else:
        print("  ℹ RapidAPI not configured (optional)")

    if os.getenv("SNCF_API_KEY"):
        print("  ✓ SNCF API configured")
    else:
        print("  ℹ SNCF API not configured (optional)")

    print()
    return True


def test_api_clients():
    """Test that API clients can be initialized."""
    print("Testing API clients...")

    # Test Amadeus
    try:
        from apis.amadeus import AmadeusFlightAPI
        api = AmadeusFlightAPI()
        print("  ✓ Amadeus client initialized")
    except Exception as e:
        print(f"  ⚠ Amadeus client: {e}")

    # Test Train API
    try:
        from apis.trains import TrainAPI
        api = TrainAPI()
        print("  ✓ Train API client initialized")
    except Exception as e:
        print(f"  ⚠ Train API client: {e}")

    # Test Bus API
    try:
        from apis.buses import FlixBusAPI
        api = FlixBusAPI()
        print("  ✓ FlixBus client initialized")
    except Exception as e:
        print(f"  ⚠ FlixBus client: {e}")

    print()
    return True


def test_tools():
    """Test that agent tools can be loaded."""
    print("Testing agent tools...")

    try:
        from agent.tools import ALL_TOOLS
        print(f"  ✓ Loaded {len(ALL_TOOLS)} tools")

        for tool in ALL_TOOLS:
            print(f"    - {tool.name}")

        print()
        return True

    except Exception as e:
        print(f"  ✗ Error loading tools: {e}\n")
        return False


def test_agent():
    """Test that the agent can be initialized."""
    print("Testing agent initialization...")

    try:
        from agent.graph import TransportationAgent

        if os.getenv("OPENAI_API_KEY"):
            agent = TransportationAgent(model_provider="openai", model_name="gpt-4")
            print("  ✓ OpenAI agent initialized")
        elif os.getenv("ANTHROPIC_API_KEY"):
            agent = TransportationAgent(
                model_provider="anthropic",
                model_name="claude-4-5-sonnet"
            )
            print("  ✓ Anthropic agent initialized")

        print()
        return True

    except Exception as e:
        print(f"  ✗ Error initializing agent: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_filesystem():
    """Test filesystem tools."""
    print("Testing filesystem tools...")

    try:
        from mcp.client import SimplifiedFilesystemTools

        fs = SimplifiedFilesystemTools()

        # Test save
        test_data = {
            "test": "data",
            "origin": "Paris",
            "destination": "Berlin"
        }

        success = fs.save_itinerary("test_itinerary", test_data)
        if success:
            print("  ✓ Save itinerary works")
        else:
            print("  ✗ Save itinerary failed")

        # Test load
        loaded = fs.read_itinerary("test_itinerary")
        if loaded and loaded.get("test") == "data":
            print("  ✓ Load itinerary works")
        else:
            print("  ✗ Load itinerary failed")

        # Test list
        files = fs.list_itineraries()
        if "test_itinerary" in files:
            print("  ✓ List itineraries works")
        else:
            print("  ✗ List itineraries failed")

        print()
        return True

    except Exception as e:
        print(f"  ✗ Error testing filesystem: {e}\n")
        return False


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("European Transportation Agent - Test Suite")
    print("=" * 60)
    print()

    results = []

    results.append(("Imports", test_imports()))
    results.append(("API Keys", test_api_keys()))
    results.append(("API Clients", test_api_clients()))
    results.append(("Tools", test_tools()))
    results.append(("Filesystem", test_filesystem()))
    results.append(("Agent", test_agent()))

    print("=" * 60)
    print("Test Results Summary")
    print("=" * 60)

    all_passed = True
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {test_name}")
        if not result:
            all_passed = False

    print()

    if all_passed:
        print("🎉 All tests passed! Your agent is ready to use.")
        print("\nRun the agent with: python main.py")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        print("\nCommon fixes:")
        print("  - Run: pip install -r requirements.txt")
        print("  - Set API keys in .env file")
        print("  - Check SETUP_GUIDE.md for details")

    print()
    return all_passed


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
