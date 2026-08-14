"""Generic tool listing and execution endpoints."""

from typing import Any

from fastapi import APIRouter, Query

from app.schemas.tools import ToolExecuteRequest
from app.services.doe_service import call_tool
from app.services.tools import get_tool_specs

router = APIRouter()


@router.get("")
async def list_tools(
    category: str | None = Query(None, description="Filter by category (e.g. 'experiments')."),
) -> dict[str, Any]:
    """List all available process-improve tool specs.

    Optionally filter by category.  Returns the specs in Anthropic
    ``tools=`` format so they can be inspected by the frontend or
    forwarded to an LLM integration.
    """
    specs = get_tool_specs(category=category)
    return {"tools": specs, "count": len(specs)}


@router.post("/execute")
async def execute_tool(request: ToolExecuteRequest) -> dict[str, Any]:
    """Execute a process-improve tool by name.

    Same path as the agent chat loop: the call runs off the event loop
    via ``asyncio.to_thread`` and, when ``settings.tool_safe_mode`` is
    on (the default), is dispatched into a forked subprocess by
    ``process_improve.tool_safety.safe_execute_tool_call`` with a
    wall-clock cap of ``settings.tool_timeout_seconds`` (default 300 s)
    and a memory cap of ``settings.tool_memory_mb``. When safe mode is
    off, the same thread hop runs an in-process call without those
    per-call limits.
    """
    return await call_tool(request.tool_name, request.tool_input)
