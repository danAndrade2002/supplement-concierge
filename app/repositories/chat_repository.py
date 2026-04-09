import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.tables import ChatMessage


class ChatRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def load_history(self, user_id: uuid.UUID, limit: int = 10) -> list[dict]:
        result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.user_id == user_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        rows = result.scalars().all()
        rows.reverse()
        return [
            {"role": "user" if r.role == "user" else "model", "content": r.content}
            for r in rows
        ]

    async def save_message(self, user_id: uuid.UUID, role: str, content: str) -> None:
        self.db.add(ChatMessage(user_id=user_id, role=role, content=content))
        await self.db.commit()
