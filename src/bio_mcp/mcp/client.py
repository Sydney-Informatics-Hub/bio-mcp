import asyncio
from contextlib import AsyncExitStack
from typing import List, Optional, Dict, Any

from anthropic import Anthropic
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from collections import defaultdict
import logging
import textwrap
from bio_mcp.globals import ANTHROPIC_MODEL
from bio_mcp.mcp.prompts import MASTER_PROMPT

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

def render_search_results(entries: List[Dict]) -> str:
    """
    Render search_containers results into a human-friendly print
    with instructions to inspect the container on CVMFS
    """
    if not entries:
        return "No matching conruntainers found."
    
    # Group entries by tool_name
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        grouped[entry["tool_name"]].append(entry)

    blocks: list[str] = []

    for tool_name, tool_entries in sorted(grouped.items()):
        version_count = len(tool_entries)

        # Select most recent version by mtime
        latest = max(tool_entries, key=lambda e: e.get("mtime", 0))

        latest_tag = latest.get("tag", "unknown")
        latest_path = latest.get("path", "<missing path>")

        block = f"""Tool: {tool_name}
Versions available: {version_count}
Latest version: {latest_tag}

To use the latest version:
  singularity exec {latest_path} <command>
"""
        blocks.append(block.rstrip())

    return "\n\n---\n\n".join(blocks)

def render_startup_message(tools) -> None:
    print("\nConnected to BioCLI!\n")
    print("Available tools:\n")

    for tool in tools:
        print(f"  {tool.name}")
        if tool.description:
            desc = textwrap.fill(
                tool.description.strip(),
                width=76,
                initial_indent="    ",
                subsequent_indent="    ",
            )
            print(f"{desc}\n")

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic()
        self.anthropic_model = ANTHROPIC_MODEL

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server

        - Validates server
        - Sets up proper communication channels
        - Initialises the session and lists registered MCP tools
        
        Args:
            server_script_path: Path to the server script (.py)
        """
        is_python = server_script_path.endswith(".py")
        if not is_python:
            raise ValueError("Server script must be a .py or .js file")

        server_params = StdioServerParameters(
            command="python", args=[server_script_path], env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        await self.session.initialize()

        response = await self.session.list_tools()
        tools = response.tools
        render_startup_message(tools)

    async def process_query(self, query: str) -> str:
        """
        Process a query using Claude and registered MCP tools.

        - Maintains conversation context
        - Handles Claude’s responses and tool calls
        - Manages the message flow between Claude and tools
        
        Tool handling:
            - Modify to handle specific tool types
            - Custom error handling for tool calls

        Response processing:
            - Combines results into a coherent response
            - Customise how tool results are formatted
            - Add response filtering or transformation
            - Implement custom logging
        """
        # prompt engineer the LLM tone and persona
        messages = [ {"role": "user", "content": query} ]

        response = await self.session.list_tools()
        available_tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }
            for tool in response.tools
        ]

        # Initial Claude API call
        response = self.anthropic.messages.create(
            model=self.anthropic_model,
            max_tokens=1000,
            system = MASTER_PROMPT,
            messages=messages,
            tools=available_tools,
        )

        logging.info(f"Initial Claude API call:\n{response}\n")

        # Process response and handle tool calls
        final_text = []

        assistant_message_content = []
        for content in response.content:
            if content.type == "text":
                final_text.append(content.text)
                assistant_message_content.append(content)
            elif content.type == "tool_use":
                tool_name = content.name
                tool_args = content.input

                # Execute tool call
                result = await self.session.call_tool(tool_name, tool_args)
                final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")

                assistant_message_content.append(content)
                messages.append(
                    {"role": "assistant", "content": assistant_message_content}
                )
                messages.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": content.id,
                                "content": result.content,
                            }
                        ],
                    }
                )

                # TODO: If the tool_names used is search_containers, run render_search_contaienrs?

                # Get next response from Claude
                response = self.anthropic.messages.create(
                    model=self.anthropic_model,
                    max_tokens=1000,
                    messages=messages,
                    tools=available_tools,
                )

                logging.info(f"Next response from Claude:\n{response}\n")

                final_text.append(response.content[0].text)


        return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop
        - Provides a simple command-line interface
        - Handles user input and displays responses
        - Allows graceful exit
        """

        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")
        # TODO: Provide example queries, usage etc.

        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() == "quit":
                    break

                response = await self.process_query(query)

                print("\n" + response)

            except Exception as e:
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()


async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)

    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    import sys

    asyncio.run(main())
