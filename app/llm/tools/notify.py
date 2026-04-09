import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.reminder_repository import ReminderRepository
from app.llm.tools.tool_interface import ITool

class NotifyTool(ITool):
    """LLM tool that schedules a low-stock reminder."""

    def __init__(self, db: AsyncSession, user_id: uuid.UUID):
        self.reminder_repo = ReminderRepository(db)
        self.user_id = user_id

    async def execute(self, params: dict[str, Any]) -> str:
        product_name = params.get("product_name", "")
        days_until_empty = params.get("days_until_empty", 0)

        reminder = await self.reminder_repo.create(
            user_id=self.user_id,
            product_name=product_name,
            days_until_empty=days_until_empty,
        )
        return (
            f"Reminder set: I will notify the user about '{reminder.product_name}' "
            f"on {reminder.trigger_date.isoformat()} ({days_until_empty} days from now)."
        )
