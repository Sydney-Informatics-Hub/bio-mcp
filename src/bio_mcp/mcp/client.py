import asyncio
import json
import logging
import textwrap
from collections import defaultdict
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional

from anthropic import Anthropic
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from bio_mcp.globals import ANTHROPIC_MODEL
from bio_mcp.mcp.prompts import MASTER_PROMPT, TOOL_SELECT_PROMPT, ToolSelectionResult

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

    def skill_tool_select(self, user_query: str, tools) -> ToolSelectionResult:
        """
        Decide whether an MCP tool should be used before it is called. This is to prevent the LLM providing an answer without the tool being used
        """
        tool_summaries = [
            {
                "name": t.name,
                "description": t.description,
                "inputSchema": t.inputSchema,
            }
            for t in tools
        ]

        messages = [
            {
                "role": "user",
                "content": (
                    f"User question:\n{user_query}\n\n"
                    f"Available tools:\n"
                    f"{json.dumps(tool_summaries, indent=2)}\n\n"
                    f"{TOOL_SELECT_PROMPT}"
                ),
            }
        ]

        response = self.anthropic.messages.create(
            model=self.anthropic_model,
            system=MASTER_PROMPT,
            max_tokens=400,
            messages=messages,
        )

        text = response.content[0].text.strip()

        # Remove code backticks from output if present
        if text.startswith("```"):
            text = text[3:]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
            if text.endswith("```"):
                text = text[:-3].rstrip()

        try:
            result: ToolSelectionResult = json.loads(text)
        except json.JSONDecodeError:
            raise RuntimeError(f"Tool selection skill returned invalid JSON:\n{text}")

        # No hallucinating if a tool isn't selected
        if result["decision"] == "use_tool":
            if not result.get("tool_name"):
                raise RuntimeError("Skill error: tool_name missing")
        else:
            result["tool_name"] = None

        return result

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
