from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.tables import User


class UserRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create(self, phone_number: str) -> User:

        result: User | None = await self.db.execute(
            select(User).where(User.phone_number == phone_number)
        )
        user: User | None = result.scalar_one_or_none()
        if user is None:
            user = User(phone_number=phone_number, allergies=[])
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
        return user
