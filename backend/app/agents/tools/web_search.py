import os

from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.tools import tool

from app.core.config import settings

os.environ["TAVILY_API_KEY"] = getattr(settings, "TAVILY_API_KEY", "")


@tool
async def web_search(query: str) -> str:
    """Search the web for current information. Use when user asks about recent events."""
    search = TavilySearchResults(max_results=3)
    results = await search.ainvoke(query)

    formatted: list[str] = []
    for r in results:
        formatted.append(f"Source: {r['url']}\n{r['content']}\n")

    return "\n---\n".join(formatted)
