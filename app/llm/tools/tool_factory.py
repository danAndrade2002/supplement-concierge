import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.tools.notify import NotifyTool
from app.llm.tools.search import SearchTool
from app.llm.tools.tool_interface import ITool
from typing import Optional
logger = logging.getLogger(__name__)


class ToolFactory:

    def __init__(self, db: AsyncSession, user_id: uuid.UUID):
        self._tools: dict[str, ITool] = {
            "search": SearchTool(),
            "notify": NotifyTool(db, user_id),
        }

    def build_tool(self, action_name: str) -> Optional[ITool]:
        tool = self._tools.get(action_name.lower())
        if tool is None:
            logger.error("Unknown action requested: %s", action_name)
            raise ValueError(f"Unknown action: {action_name}")
        return tool
        
    # async def execute(self, action_name: str, params: dict[str, Any]) -> str:
    #     tool = self._tools.get(action_name)
    #     if tool is None:
    #         logger.error("Unknown action requested: %s", action_name)
    #         return f"Unknown action: {action_name}"
    #     return await tool.execute(params)
