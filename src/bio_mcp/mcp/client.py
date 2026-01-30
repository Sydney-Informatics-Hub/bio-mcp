import asyncio
import json
import os
import re
from contextlib import AsyncExitStack
from typing import List, Optional

from anthropic import Anthropic
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()


def extract_entry_names(query: str) -> List[str]:
    """
    Get lowercase tokens that could be e.g. containers or reference data names.
    """
    tokens = re.findall(r"[a-zA-Z0-9_+-]+", query.lower())
    return list(dict.fromkeys(tokens))

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic()
        self.anthropic_model = "claude-haiku-4-5-20251001"

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server

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
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def process_query(self, query: str) -> str:
        """
        No LLM use
        """
        # Get possible entry names from user input
        entry_names = extract_entry_names(query)
        if not entry_names:
            return "No matching tools or data in query"

        result = await self.session.call_tool( # type: ignore
            "search_entry_name", {"entry_names": entry_names}
        )

        # TODO: triage entry names with fuzzy matching vs. tool recommendations
        payload = None
        for item in result.content:
            if item.type == "text":
                payload = item.text
                break

        if not payload:
            return "No response from search_entry_name."

        data = json.loads(payload)
        if not data.get("found") and not data.get("missing"):
            return "No matching entries found in cache."

        return self.format_with_llm(query, data)

    def format_with_llm(self, query: str, data: dict) -> str:
        """
        Format the search result with Claude, using only the output JSON.
        """
        content_json = json.dumps(data, indent=2)
        system_prompt = (
            "You are formatting tool lookup results. "
            "Only use the JSON provided; do not add extra tools. "
            "Be concise and clear."
        )
        user_prompt = (
            "User query:\n"
            f"{query}\n\n"
            "Lookup result JSON:\n"
            f"{content_json}\n\n"
            "Return a brief summary and a bullet list of found tools. "
            "If missing tools exist, list them under 'Missing'. "
            "If suggestions exist, include them under 'Suggestions'."
        )

        if not self.anthropic_model:
            return (
                "ANTHROPIC_MODEL is not set. "
                "Set it to a model available in your Anthropic account."
            )

        try:
            response = self.anthropic.messages.create(
                model=self.anthropic_model,
                max_tokens=400,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except Exception as exc:
            return (
                "LLM formatting failed. Check ANTHROPIC_MODEL and API key. "
                f"Error: {exc}"
            )

        return response.content[0].text if response.content else "No LLM response."

    async def process_query_boilerplate(self, query: str) -> str:
        """Process a query using Claude and available tools"""
        messages = [
            {
                "role": "user",
                "content": query
            }
        ]

        response = await self.session.list_tools()
        available_tools = [{
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in response.tools]

        # Initial Claude API call
        response = self.anthropic.messages.create(
            model=self.anthropic_model,
            max_tokens=1000,
            messages=messages,
            tools=available_tools
        )

        # Process response and handle tool calls
        final_text = []

        assistant_message_content = []
        for content in response.content:
            if content.type == 'text':
                final_text.append(content.text)
                assistant_message_content.append(content)
            elif content.type == 'tool_use':
                tool_name = content.name
                tool_args = content.input

                # Execute tool call
                result = await self.session.call_tool(tool_name, tool_args)
                final_text.append(f"[Calling tool {tool_name} with args {tool_args}]")

                assistant_message_content.append(content)
                messages.append({
                    "role": "assistant",
                    "content": assistant_message_content
                })
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": content.id,
                            "content": result.content
                        }
                    ]
                })

                # Get next response from Claude
                response = self.anthropic.messages.create(
                    model=self.anthropic_model,
                    max_tokens=1000,
                    messages=messages,
                    tools=available_tools
                )

                final_text.append(response.content[0].text)

        return "\n".join(final_text)
    
    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")
        # TODO: Provide example queries, usage etc.

        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() == "quit":
                    break

                #response = await self.process_query(query)
                response = await self.process_query_boilerplate(query)
                
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
