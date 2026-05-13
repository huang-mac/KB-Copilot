from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_tool_registry
from app.tools.registry import ToolRegistry

router = APIRouter(prefix="/tools", tags=["tools"])


@router.post("/{tool_name}")
async def invoke_tool(
    tool_name: str,
    body: dict,
    tool_registry: Annotated[ToolRegistry, Depends(get_tool_registry)],
) -> dict:
    tool = tool_registry.get(tool_name)
    if tool is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{tool_name}' not found",
        )
    return await tool.execute(**body)
