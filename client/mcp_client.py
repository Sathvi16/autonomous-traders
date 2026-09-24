import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]


# ============================================================
# MCP SERVER MODULES
# ============================================================

SERVER_MODULES = {
    "accounts": "servers.accounts_server",
    "market": "servers.market_server",
    "research": "servers.research_server",
}


# ============================================================
# EXTRACT STRUCTURED CONTENT
# ============================================================

def get_structured_content(result):
    """
    Support both:

        structuredContent

    and:

        structured_content
    """

    value = getattr(
        result,
        "structuredContent",
        None
    )

    if value is not None:
        return value

    value = getattr(
        result,
        "structured_content",
        None
    )

    return value


# ============================================================
# GET ERROR FLAG
# ============================================================

def get_error_flag(result) -> bool:
    """
    Support both:

        isError

    and:

        is_error
    """

    value = getattr(
        result,
        "isError",
        None
    )

    if value is not None:
        return bool(value)

    value = getattr(
        result,
        "is_error",
        None
    )

    if value is not None:
        return bool(value)

    return False


# ============================================================
# EXTRACT MCP RESULT
# ============================================================

def extract_tool_result(result):
    """
    Convert MCP CallToolResult into normal Python data.
    """

    # --------------------------------------------------------
    # 1. Structured content
    # --------------------------------------------------------

    structured = get_structured_content(result)

    if structured is not None:

        if (
            isinstance(structured, dict)
            and "result" in structured
            and len(structured) == 1
        ):
            return structured["result"]

        return structured

    # --------------------------------------------------------
    # 2. Text content
    # --------------------------------------------------------

    content = getattr(
        result,
        "content",
        []
    )

    for content_item in content:

        text = getattr(
            content_item,
            "text",
            None
        )

        if text is None:
            continue

        try:
            return json.loads(text)

        except (
            json.JSONDecodeError,
            TypeError
        ):
            return text

    # --------------------------------------------------------
    # 3. Nothing returned
    # --------------------------------------------------------

    return None


# ============================================================
# CALL MCP TOOL
# ============================================================

async def call_mcp_tool(
    server_name: str,
    tool_name: str,
    arguments: dict | None = None,
):
    """
    Start an MCP server using STDIO,
    connect to it,
    discover its tools,
    call the requested tool,
    and return the result.
    """

    # --------------------------------------------------------
    # Validate server
    # --------------------------------------------------------

    if server_name not in SERVER_MODULES:

        raise ValueError(
            f"Unknown MCP server '{server_name}'. "
            f"Available servers: "
            f"{list(SERVER_MODULES.keys())}"
        )

    server_module = SERVER_MODULES[
        server_name
    ]

    # --------------------------------------------------------
    # Configure subprocess
    # --------------------------------------------------------

    server_params = StdioServerParameters(
        command=sys.executable,
        args=[
            "-m",
            server_module,
        ],
        cwd=str(PROJECT_ROOT),
    )

    # --------------------------------------------------------
    # Start MCP server
    # --------------------------------------------------------

    async with stdio_client(
        server_params,
        errlog=sys.stderr
    ) as (
        read_stream,
        write_stream,
    ):

        # ----------------------------------------------------
        # Create session
        # ----------------------------------------------------

        async with ClientSession(
            read_stream,
            write_stream,
        ) as session:

            # ------------------------------------------------
            # Initialize
            # ------------------------------------------------

            await session.initialize()

            # ------------------------------------------------
            # Discover tools
            # ------------------------------------------------

            tools_result = await session.list_tools()

            available_tools = [
                tool.name
                for tool in tools_result.tools
            ]

            # ------------------------------------------------
            # Validate requested tool
            # ------------------------------------------------

            if tool_name not in available_tools:

                raise ValueError(
                    f"Tool '{tool_name}' is not available "
                    f"on MCP server '{server_name}'. "
                    f"Available tools: "
                    f"{available_tools}"
                )

            # ------------------------------------------------
            # Call tool
            # ------------------------------------------------

            result = await session.call_tool(
                tool_name,
                arguments or {},
            )

            # ------------------------------------------------
            # Check MCP tool error
            # ------------------------------------------------

            if get_error_flag(result):

                return {
                    "success": False,
                    "error": extract_tool_result(
                        result
                    ),
                }

            # ------------------------------------------------
            # Return successful result
            # ------------------------------------------------

            return extract_tool_result(
                result
            )


# ============================================================
# TEST CLIENT
# ============================================================

async def test_mcp_client():

    result = await call_mcp_tool(
        "market",
        "get_price",
        {
            "stock": "AAPL"
        }
    )

    print(
        json.dumps(
            result,
            indent=4
        )
    )


# ============================================================
# DIRECT EXECUTION
# ============================================================

if __name__ == "__main__":

    asyncio.run(
        test_mcp_client()
    )