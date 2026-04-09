from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.tables import User


class UserRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create(self, whatsapp_id: str) -> User:
        result = await self.db.execute(
            select(User).where(User.whatsapp_id == whatsapp_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            user = User(whatsapp_id=whatsapp_id, allergies=[])
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
        return user
