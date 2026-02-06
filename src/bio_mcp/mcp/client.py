import asyncio
import json
import logging
import textwrap
from collections import defaultdict
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional, Literal

from anthropic import Anthropic
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from bio_mcp.globals import ANTHROPIC_MODEL

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

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

def route_query(query: str) -> Literal["search", "describe", "recommend", "none"]:
    """Route query to appropriate skill based on simple keyword matching
    - In future, can be replaced with a more sophisticated routing mechanism (e.g. skill)
    """
    q = query.lower()
    search_phrases = [
        "is installed",
        "is it installed",
        "installed?",
        "where can i use",
        "where do i use",
        "where can i run",
        "where is",
        "available version",
        "what versions are available",
        "latest version",
        "latest",
        "are available?"
    ]

    describe_phrases = [
        "what does",
        "what is",
        "purpose of",
        "describe",
    ]
    
    recommend_phrases = [
        "what tool can be used",
        "what tool should i use",
        "what can i use to",
        "can be used to",
        "can be used for",
        "tool for",
        "used to generate",
        "used to build",
    ]

    if any(p in q for p in search_phrases):
        return "search"
    elif any(p in q for p in describe_phrases):
        return "describe"
    elif any(p in q for p in recommend_phrases):
        # Not implemented yet, blocked by metadata gaps
        return "recommend"
    else:
        return "none"

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic()
        self.anthropic_model = ANTHROPIC_MODEL
        self.tools: List[Dict[str, Any]] = []

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

        self.tools = await self.list_tools()
        render_startup_message(self.tools)

    async def list_tools(self) -> List[Dict[str, Any]]:
        """List registered MCP tools"""
        if self.session is None:
            raise RuntimeError("Not connected to server")

        response = await self.session.list_tools()
        return [
            {"name": tool.name, "description": tool.description, "input_schema": tool.inputSchema}
            for tool in response.tools
        ]

        
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
        messages = [{"role": "user", "content": query}]

        # Get registerd MCP tools
        tools_response = await self.session.list_tools()
        tools = tools_response.tools

        available_tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }
            for tool in tools
        ]

        # Skill: decide on a tool to use, no computation yet
        decision = self.skill_tool_select(query, tools)

        # If a tool doesn't apply, do not use LLM to provide an answer
        if decision["decision"] == "no_tool":
            return (
                "I couldn't find a suitable tool for this question.\n\n"
                f"Reason: {decision['reason']}"
            )

        # Tool selected
        tool_name = decision["tool_name"]
        reason = decision["reason"]

        tool = next(t for t in tools if t.name == tool_name)
        selected_tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
            }
        ]

        intro = (
            f"I’m going to use the **{tool_name}** tool.\n\nWhy this tool: {reason}\n"
        )

        # Initial Claude API call
        response = self.anthropic.messages.create(
            model=self.anthropic_model,
            max_tokens=1000,
            system=MASTER_PROMPT,  # Set tone and persona of LLM
            messages=messages,
            tools=selected_tools,
            tool_choice={"type": "tool", "name": tool_name} # Enforce use of selected tool on first response, can be relaxed in future iterations
        )

        # logging.info(f"Initial Claude API call:\n{response}\n")

        # Process response and handle tool calls
        final_text = []
        assistant_message_content = []

        saw_tool_use = False

        # Process response
        for content in response.content:
            if content.type == "text":
                final_text.append(content.text)
                assistant_message_content.append(content)

            elif content.type == "tool_use":
                if content.name != tool_name:
                    raise RuntimeError(
                        f"Selected tool was {tool_name}, but model requested {content.name}"
                    )
                saw_tool_use = True
                # Add intro BEFORE tool_use in same assistant turn
                assistant_message_content.insert(
                    0,
                    {
                        "type": "text",
                        "text": intro,
                    },
                )
                tool_name = content.name
                tool_args = content.input

                assistant_message_content.append(content)

                # Add assistant message (intro selection and use)
                messages.append(
                    {"role": "assistant", "content": assistant_message_content}
                )

                # Execute tool call
                result = await self.session.call_tool(content.name, content.input)
                final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")

                # Return tool results to Claude
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

                # Get next response from Claude
                response = self.anthropic.messages.create(
                    model=self.anthropic_model,
                    max_tokens=1000,
                    system=MASTER_PROMPT,
                    messages=messages,
                    tools=selected_tools,
                )

                # logging.info(f"Next response from Claude:\n{response}\n")

                # Collect explanation text
                for block in response.content:
                    if block.type == "text":
                        final_text.append(block.text)

                break  # single-tool invariant enforced by skill

        if not saw_tool_use:
            raise RuntimeError(f"Expected tool use for selected tool: {tool_name}")

        return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop
        - Provides a simple command-line interface
        - Handles user input and displays responses
        - Allows graceful exit
        """

        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")

        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() == "quit":
                    print("\nExiting...")
                    break

                response = await self.process_query(query)

                print("\n" + response)

            except (EOFError, KeyboardInterrupt):
                print('\nExiting...')
                break

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
