"""MCP (Model Context Protocol) client integration using direct Tavily API."""

import logging

import httpx
from langchain_core.tools import BaseTool, tool

from ..settings import get_settings

logger = logging.getLogger(__name__)


# TODO: implement properly
class MCPClient:
    """Client for interacting with MCP servers - simplified for Tavily."""

    def __init__(self):
        self.settings = get_settings()
        self.tools: list[BaseTool] = []

    async def initialize_tavily(self) -> None:
        """Initialize Tavily search tool directly."""
        if not self.settings.tavily_api_key:
            logger.warning("TAVILY_API_KEY not set, skipping Tavily initialization")
            return

        try:
            # Create Tavily search tool directly
            @tool
            async def tavily_search(query: str) -> str:
                """Search the web using Tavily API."""
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://api.tavily.com/search",
                        json={
                            "api_key": self.settings.tavily_api_key,
                            "query": query,
                            "search_depth": "basic",
                            "include_answer": True,
                            "include_raw_content": False,
                            "max_results": 3,
                        },
                        timeout=30.0,
                    )
                    response.raise_for_status()
                    data = response.json()

                    # Format the results
                    results = []
                    if data.get("answer"):
                        results.append(f"Answer: {data['answer']}")

                    for result in data.get("results", []):
                        results.append(f"Title: {result.get('title', 'N/A')}")
                        results.append(f"URL: {result.get('url', 'N/A')}")
                        if result.get("content"):
                            results.append(f"Content: {result['content'][:200]}...")
                        results.append("---")

                    return "\n".join(results) if results else "No results found."

            self.tools = [tavily_search]
            logger.info("Initialized Tavily search tool")

        except Exception as e:
            logger.error(f"Failed to initialize Tavily: {e}")
            # Fallback to empty tools list
            self.tools = []

    async def get_tools(self) -> list[BaseTool]:
        """Get all available MCP tools as LangChain tools."""
        if not self.tools:
            await self.initialize_tavily()
        return self.tools

    async def close(self) -> None:
        """Close MCP session (no-op for direct API)."""
        pass


# Global MCP client instance
_mcp_client: MCPClient | None = None


async def get_mcp_client() -> MCPClient:
    """Get or create global MCP client instance."""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client


async def get_mcp_tools() -> list[BaseTool]:
    """Get all available MCP tools."""
    client = await get_mcp_client()
    return await client.get_tools()
