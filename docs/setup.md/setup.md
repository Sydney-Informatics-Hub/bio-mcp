## How to setup MCP

Following https://modelcontextprotocol.io/docs/develop/build-server.

On a NeCTAR VM:

```bash
# Setup environment
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env

# Create a new directory for our project
uv init bio-mcp
cd bio-mcp

# Create virtual environment and activate it
uv venv
source .venv/bin/activate

# Install dependencies
# server
uv add "mcp[cli]" httpx
# client
uv add anthropic python-dotenv

# Create our server and client files
touch server.py client.py
rm main.py
```

## How to set up your API key

On https://platform.claude.com/dashboard with a paid account, create a new API key.

```bash
# Create a `.env` to store the API key
echo "ANTHROPIC_API_KEY=your-api-key-goes-here" > .env

# Add `.env` to `.gitignore`
echo ".env" >> .gitignore
```