"""MCP client for filesystem operations using Model Context Protocol."""
import json
import asyncio
from typing import Optional, Dict, Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPFilesystemClient:
    """
    Client for MCP filesystem server.
    Provides tools to save and read travel itineraries.
    """

    def __init__(self, base_path: str = "./saved_itineraries"):
        """
        Initialize MCP filesystem client.

        Args:
            base_path: Base directory for saved files
        """
        import os
        # Convert to absolute path for MCP server
        self.base_path = os.path.abspath(base_path)
        # Ensure directory exists
        os.makedirs(self.base_path, exist_ok=True)

        self.session: Optional[ClientSession] = None
        self.server_params = StdioServerParameters(
            command="npx",
            args=[
                "-y",
                "@modelcontextprotocol/server-filesystem",
                self.base_path
            ]
        )

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()

    async def connect(self):
        """Connect to MCP filesystem server."""
        # stdio_client returns a context manager that yields (read_stream, write_stream)
        self._context = stdio_client(self.server_params)
        streams = await self._context.__aenter__()
        # Create session from streams
        read_stream, write_stream = streams
        self.session = ClientSession(read_stream, write_stream)
        await self.session.__aenter__()

    async def disconnect(self):
        """Disconnect from MCP filesystem server."""
        if hasattr(self, 'session') and self.session:
            await self.session.__aexit__(None, None, None)
        if hasattr(self, '_context') and self._context:
            await self._context.__aexit__(None, None, None)

    async def save_itinerary(
        self,
        filename: str,
        content: Dict[str, Any]
    ) -> bool:
        """
        Save travel itinerary to file.

        Args:
            filename: Name of the file (will be saved as JSON)
            content: Itinerary data to save

        Returns:
            True if successful, False otherwise
        """
        if not self.session:
            print("Not connected to MCP server")
            return False

        try:
            # Format content as JSON
            json_content = json.dumps(content, indent=2)

            # Use MCP write_file tool
            # MCP server needs full path within the allowed directory
            import os
            full_path = os.path.join(self.base_path, f"{filename}.json")
            result = await self.session.call_tool(
                "write_file",
                arguments={
                    "path": full_path,
                    "content": json_content
                }
            )

            # Check if operation succeeded
            if result.isError:
                error_msg = result.content[0].text if result.content else "Unknown error"
                print(f"MCP write error: {error_msg}")
                return False

            return True

        except Exception as e:
            print(f"Error saving itinerary: {e}")
            return False

    async def read_itinerary(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Read saved itinerary from file.

        Args:
            filename: Name of the file to read

        Returns:
            Itinerary data or None if error
        """
        if not self.session:
            print("Not connected to MCP server")
            return None

        try:
            # Use MCP read_file tool
            # MCP server needs full path within the allowed directory
            import os
            full_path = os.path.join(self.base_path, f"{filename}.json")
            result = await self.session.call_tool(
                "read_file",
                arguments={
                    "path": full_path
                }
            )

            # MCP returns a list of content items
            if result.content and len(result.content) > 0:
                # Get the text content from the first item
                content_item = result.content[0]
                if hasattr(content_item, 'text'):
                    content_text = content_item.text
                else:
                    content_text = str(content_item)

                # Parse JSON
                return json.loads(content_text)

            return None

        except Exception as e:
            print(f"Error reading itinerary: {e}")
            return None

    async def list_itineraries(self) -> list[str]:
        """
        List all saved itineraries.

        Returns:
            List of filenames (without .json extension)
        """
        if not self.session:
            print("Not connected to MCP server")
            return []

        try:
            # Use MCP list_directory tool
            # List the base directory itself
            result = await self.session.call_tool(
                "list_directory",
                arguments={
                    "path": self.base_path
                }
            )

            # Extract filenames from MCP response
            files = []
            if result.content and len(result.content) > 0:
                # Get the text content
                content_item = result.content[0]
                if hasattr(content_item, 'text'):
                    # Parse the directory listing
                    import re
                    text = content_item.text
                    # Extract .json filenames
                    json_files = re.findall(r'(\w+)\.json', text)
                    files = json_files

            return files

        except Exception as e:
            print(f"Error listing itineraries: {e}")
            return []


class SimplifiedFilesystemTools:
    """
    Simplified filesystem tools that don't require async MCP.
    Used as a fallback when MCP is not available.
    """

    def __init__(self, base_path: str = "./saved_itineraries"):
        """Initialize with base path."""
        self.base_path = base_path
        import os
        os.makedirs(base_path, exist_ok=True)

    def save_itinerary(self, filename: str, content: Dict[str, Any]) -> bool:
        """Save itinerary to JSON file."""
        try:
            import os
            filepath = os.path.join(self.base_path, f"{filename}.json")

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(content, f, indent=2, ensure_ascii=False)

            print(f"Itinerary saved to: {filepath}")
            return True

        except Exception as e:
            print(f"Error saving itinerary: {e}")
            return False

    def read_itinerary(self, filename: str) -> Optional[Dict[str, Any]]:
        """Read itinerary from JSON file."""
        try:
            import os
            filepath = os.path.join(self.base_path, f"{filename}.json")

            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)

        except Exception as e:
            print(f"Error reading itinerary: {e}")
            return None

    def list_itineraries(self) -> list[str]:
        """List all saved itineraries."""
        try:
            import os
            files = os.listdir(self.base_path)
            return [f.replace('.json', '') for f in files if f.endswith('.json')]

        except Exception as e:
            print(f"Error listing itineraries: {e}")
            return []


# Example usage
if __name__ == "__main__":
    async def test_mcp():
        """Test MCP client."""
        async with MCPFilesystemClient() as client:
            # Save test itinerary
            test_data = {
                "origin": "Paris",
                "destination": "Berlin",
                "date": "2025-11-01",
                "options": [
                    {"type": "flight", "price": 89.99, "duration": "PT2H"},
                    {"type": "train", "price": 75.00, "duration": "PT8H"}
                ]
            }

            await client.save_itinerary("test_itinerary", test_data)

            # Read it back
            loaded = await client.read_itinerary("test_itinerary")
            print("Loaded:", loaded)

            # List all
            files = await client.list_itineraries()
            print("Files:", files)

    # Test simplified version (synchronous)
    print("Testing simplified filesystem tools...")
    fs = SimplifiedFilesystemTools()

    test_data = {
        "origin": "Paris",
        "destination": "Berlin",
        "options": []
    }

    fs.save_itinerary("test", test_data)
    loaded = fs.read_itinerary("test")
    print("Loaded:", loaded)
