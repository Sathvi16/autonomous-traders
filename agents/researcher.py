from client.mcp_client import call_mcp_tool


async def research_stock(
    stock: str,
    prices: list[dict]
) -> dict:
    """
    Ask the Research MCP server to analyze
    already-fetched market data.
    """

    result = await call_mcp_tool(
        server_name="research",
        tool_name="research_stock",
        arguments={
            "stock": stock,
            "prices": prices
        }
    )

    return result