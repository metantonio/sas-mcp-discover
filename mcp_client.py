import asyncio
import json
import logging
from contextlib import asynccontextmanager
import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.client.sse import sse_client
from auth import get_ssl_verify

logger = logging.getLogger("mcp_client")


def _build_headers(token):
    headers = {
        "Accept": "application/json, text/event-stream",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


@asynccontextmanager
async def connect_mcp_session(url: str, token: str, cfg: dict = None):
    """
    Connect to an MCP Server over HTTP or HTTPS.
    Supports both Streamable HTTP (default) and SSE transports,
    with custom SSL verification and corporate CA certificate support.
    """
    cfg = cfg or {}
    verify_ssl = get_ssl_verify(cfg)
    headers = _build_headers(token)
    transport_pref = cfg.get("transport", "auto").lower()

    use_sse = transport_pref == "sse" or url.rstrip("/").endswith("/sse")

    timeout = httpx2.Timeout(connect=20.0, read=180.0, write=60.0, pool=30.0)

    if not use_sse:
        try:
            async with httpx2.AsyncClient(
                headers=headers,
                verify=verify_ssl,
                timeout=timeout,
                follow_redirects=True,
            ) as http_client:
                async with streamable_http_client(url, http_client=http_client) as (read_stream, write_stream):
                    async with ClientSession(read_stream, write_stream, read_timeout_seconds=180.0) as session:
                        await session.initialize()
                        yield session
                        return
        except Exception as e:
            # If transport is explicitly streamable_http or auto without SSE fallback needed
            if transport_pref == "streamable_http":
                raise
            logger.warning(f"Streamable HTTP connection attempt failed ({e}), attempting SSE transport fallback...")

    # SSE fallback or direct SSE mode
    def sse_client_factory(**kwargs):
        req_headers = dict(headers)
        if "headers" in kwargs and kwargs["headers"]:
            req_headers.update(kwargs["headers"])
        req_timeout = kwargs.get("timeout", timeout)
        return httpx2.AsyncClient(
            headers=req_headers,
            verify=verify_ssl,
            timeout=req_timeout,
            follow_redirects=True,
        )

    async with sse_client(
        url=url,
        headers=headers,
        timeout=20.0,
        sse_read_timeout=300.0,
        httpx_client_factory=sse_client_factory,
    ) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream, read_timeout_seconds=180.0) as session:
            await session.initialize()
            yield session


async def list_tools(url: str, token: str, cfg: dict = None):
    """Query available tools from the SAS MCP Server."""
    async with connect_mcp_session(url, token, cfg) as session:
        result = await session.list_tools()
        return result.tools


async def call_tool(url: str, token: str, name: str, args: dict, cfg: dict = None):
    """Execute a tool on the SAS MCP Server."""
    async with connect_mcp_session(url, token, cfg) as session:
        return await session.call_tool(name=name, arguments=args)


def run_async(fn, *a, **k):
    """Run an async function synchronously."""
    return asyncio.run(fn(*a, **k))


def extract_text(result):
    """Extract and format response text from CallToolResult or other outputs."""
    if result is None:
        return "(No response)"

    parts = []
    is_error = getattr(result, "is_error", False)
    if is_error:
        parts.append("[SERVER ERROR REPORTED]")

    contents = getattr(result, "content", None)
    if contents:
        for c in contents:
            if hasattr(c, "text"):
                parts.append(c.text)
            elif isinstance(c, dict) and "text" in c:
                parts.append(c["text"])
            elif hasattr(c, "data"):
                parts.append(f"[Binary/Media Data: {getattr(c, 'mimeType', 'unknown')}]")
            else:
                parts.append(str(c))

    structured = getattr(result, "structured_content", None)
    if structured:
        try:
            parts.append(json.dumps(structured, indent=2, ensure_ascii=False))
        except Exception:
            parts.append(str(structured))

    if not parts:
        try:
            if hasattr(result, "model_dump_json"):
                return result.model_dump_json(indent=2)
            if hasattr(result, "__dict__"):
                return json.dumps(result.__dict__, indent=2, default=str)
        except Exception:
            pass
        return str(result)

    return "\n\n".join(parts)
