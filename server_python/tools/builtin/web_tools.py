"""
Web operation tools.
Provides web fetching and search capabilities.
"""

import aiohttp
import asyncio
from typing import Optional, List
from urllib.parse import urlparse

from ..base_tool import BaseTool
from ..tool_schemas import (
    ToolResult,
    ToolParameter,
    ParameterType,
    ToolCategory,
)


class WebFetchTool(BaseTool):
    """Fetch content from a URL."""

    name = "web_fetch"
    description = """Fetches content from a specified URL.
    Processes HTML to markdown and returns the content.
    Useful for retrieving documentation, articles, etc."""
    category = ToolCategory.WEB
    version = "1.0.0"
    timeout_seconds = 30

    parameters = [
        ToolParameter(
            name="url",
            type=ParameterType.STRING,
            description="The URL to fetch content from",
            required=True,
        ),
        ToolParameter(
            name="prompt",
            type=ParameterType.STRING,
            description="Optional prompt to process the content (e.g., 'summarize this page')",
            required=False,
        ),
    ]

    async def execute(
        self,
        url: str,
        prompt: Optional[str] = None,
    ) -> ToolResult:
        """Execute the web fetch operation."""
        try:
            # Validate URL
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return ToolResult.error_result(
                    f"Invalid URL: {url}",
                    "InvalidURLError"
                )

            # Upgrade to HTTPS if needed
            if parsed.scheme == "http":
                url = url.replace("http://", "https://", 1)

            # Fetch the content
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=self.timeout_seconds),
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Agent Monitor Bot)',
                    }
                ) as response:
                    if response.status != 200:
                        return ToolResult.error_result(
                            f"HTTP {response.status}: {response.reason}",
                            "HTTPError"
                        )

                    content_type = response.headers.get('Content-Type', '')

                    if 'text/html' in content_type:
                        html = await response.text()
                        # Simple HTML to text conversion
                        # In production, use BeautifulSoup or similar
                        text = self._html_to_text(html)
                    else:
                        text = await response.text()

            # Truncate if too long
            max_length = 50000
            if len(text) > max_length:
                text = text[:max_length] + "\n\n... (content truncated)"

            result = {
                "url": url,
                "content": text,
                "length": len(text),
            }

            if prompt:
                result["note"] = f"Prompt: {prompt}"

            return ToolResult.success_result(
                text,
                **result
            )

        except aiohttp.ClientError as e:
            return ToolResult.error_result(
                f"Failed to fetch URL: {str(e)}",
                "NetworkError"
            )
        except asyncio.TimeoutError:
            return ToolResult.error_result(
                f"Request timed out after {self.timeout_seconds}s",
                "TimeoutError"
            )
        except Exception as e:
            return ToolResult.error_result(str(e), type(e).__name__)

    def _html_to_text(self, html: str) -> str:
        """Simple HTML to text conversion."""
        # Remove scripts and styles
        import re
        text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)

        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)

        # Decode HTML entities
        import html as html_module
        text = html_module.unescape(text)

        # Clean up whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)

        return text.strip()


class WebSearchTool(BaseTool):
    """Search the web for information."""

    name = "web_search"
    description = """Searches the web and returns search results.
    Provides up-to-date information for current events and recent data.
    Returns formatted search results with URLs."""
    category = ToolCategory.WEB
    version = "1.0.0"
    timeout_seconds = 30

    parameters = [
        ToolParameter(
            name="query",
            type=ParameterType.STRING,
            description="The search query",
            required=True,
            min_length=2,
        ),
        ToolParameter(
            name="max_results",
            type=ParameterType.INTEGER,
            description="Maximum number of results to return",
            required=False,
            default=5,
            min_value=1,
            max_value=20,
        ),
        ToolParameter(
            name="allowed_domains",
            type=ParameterType.ARRAY,
            description="Only include results from these domains",
            required=False,
        ),
        ToolParameter(
            name="blocked_domains",
            type=ParameterType.ARRAY,
            description="Never include results from these domains",
            required=False,
        ),
    ]

    async def execute(
        self,
        query: str,
        max_results: int = 5,
        allowed_domains: Optional[List[str]] = None,
        blocked_domains: Optional[List[str]] = None,
    ) -> ToolResult:
        """Execute the web search operation."""
        try:
            # Note: This is a placeholder implementation
            # In production, integrate with a real search API like:
            # - Google Custom Search API
            # - Bing Search API
            # - DuckDuckGo API
            # - Brave Search API

            # For now, return a placeholder response
            return ToolResult.error_result(
                "Web search functionality requires API integration. "
                "Please configure a search API provider (Google, Bing, DuckDuckGo, etc.)",
                "NotImplementedError"
            )

            # Example implementation with a real API:
            """
            async with aiohttp.ClientSession() as session:
                params = {
                    'q': query,
                    'num': max_results,
                }

                async with session.get(
                    'https://api.search-provider.com/search',
                    params=params,
                    headers={'Authorization': f'Bearer {api_key}'},
                    timeout=aiohttp.ClientTimeout(total=self.timeout_seconds),
                ) as response:
                    if response.status != 200:
                        return ToolResult.error_result(
                            f"Search API error: {response.status}",
                            "SearchAPIError"
                        )

                    data = await response.json()

                    # Filter results
                    results = []
                    for item in data.get('items', [])[:max_results]:
                        domain = urlparse(item['link']).netloc

                        if allowed_domains and domain not in allowed_domains:
                            continue
                        if blocked_domains and domain in blocked_domains:
                            continue

                        results.append({
                            'title': item.get('title'),
                            'url': item.get('link'),
                            'snippet': item.get('snippet'),
                        })

                    # Format output
                    output_lines = []
                    for i, result in enumerate(results, 1):
                        output_lines.append(f"{i}. {result['title']}")
                        output_lines.append(f"   {result['url']}")
                        output_lines.append(f"   {result['snippet']}")
                        output_lines.append("")

                    return ToolResult.success_result(
                        "\n".join(output_lines),
                        total_results=len(results),
                        query=query,
                        results=results,
                    )
            """

        except Exception as e:
            return ToolResult.error_result(str(e), type(e).__name__)
