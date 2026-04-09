import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.tables import Reminder


class ReminderRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: uuid.UUID, product_name: str, days_until_empty: int) -> Reminder:
        trigger_date = date.today() + timedelta(days=days_until_empty)
        reminder = Reminder(
            user_id=user_id,
            product_name=product_name,
            trigger_date=trigger_date,
            status="pending",
        )
        self.db.add(reminder)
        await self.db.commit()
        await self.db.refresh(reminder)
        return reminder
