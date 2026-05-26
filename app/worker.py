import asyncio
import logging
import uuid
from datetime import date

from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_process_init
from google import genai
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.constants import SYSTEM_PROMPT
from app.database import get_sync_db
from app.logging_config import configure_logging, request_id_var
from app.llm.llm_client import LLMClient
from app.llm.tools.search.search_tool import SearchTool
from app.repositories.chat_repository import ChatRepository
from app.tables import Reminder, User
from app.util.whatsapp_util import WhatsappUtil

logger = logging.getLogger(__name__)

celery_app = Celery("whats_bot", broker=settings.REDIS_URL, backend=settings.REDIS_URL)

celery_app.conf.beat_schedule = {
    "check-reminders-daily": {
        "task": "app.worker.check_reminders",
        "schedule": crontab(hour=9, minute=0),
    },
}
celery_app.conf.timezone = "America/Sao_Paulo"


@celery_app.task(name="app.worker.check_reminders")
def check_reminders():
    """Find pending reminders due today (or overdue) and send WhatsApp alerts."""
    db = get_sync_db()
    try:
        result = db.execute(
            select(Reminder, User)
            .join(User, Reminder.user_id == User.id)
            .where(Reminder.trigger_date <= date.today())
            .where(Reminder.status == "pending")
        )
        rows = result.all()

        for reminder, user in rows:
            message = (
                f"Hi! Your stock of {reminder.product_name} might be running low. "
                f"Would you like me to check today's prices?"
            )
            WhatsappUtil.send_message_sync(user.phone_number, message)
            reminder.status = "completed"
            logger.info(
                "Sent reminder to %s for '%s'", user.phone_number, reminder.product_name
            )

        db.commit()
        logger.info("Processed %d reminder(s)", len(rows))
    finally:
        db.close()


@celery_app.task(name="app.worker.run_search_and_reply")
def run_search_and_reply(
    phone_number: str,
    user_id: str,
    query: str,
    exclude_ingredients: list,
    llm_waiting_text: str,
    allergies: list,
) -> None:
    try:
        asyncio.run(_async_search_and_reply(
            phone_number, user_id, query, exclude_ingredients, llm_waiting_text, allergies,
        ))
    except Exception:
        logger.exception("run_search_and_reply failed for %s", phone_number)
        try:
            WhatsappUtil.send_message_sync(
                phone_number,
                "Sorry, something went wrong while searching. Please try again in a moment.",
            )
        except Exception:
            logger.exception("Failed to send error fallback to %s", phone_number)


async def _async_search_and_reply(
    phone_number: str,
    user_id: str,
    query: str,
    exclude_ingredients: list,
    llm_waiting_text: str,
    allergies: list,
) -> None:
    uid = uuid.UUID(user_id)

    # Create a fresh engine inside this event loop so asyncpg's connection pool
    # is always bound to the loop that asyncio.run() just created.
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        # 1. Run the search
        search_tool = SearchTool()
        tool_result = await search_tool.execute({"query": query, "exclude_ingredients": exclude_ingredients})
        logger.info("Search completed for user %s query=%r", user_id, query)

        # 2. Load history — now includes user message + "please wait" assistant message
        async with session_factory() as db:
            chat_repo = ChatRepository(db)
            history = await chat_repo.load_history(uid)

        # 3. Build contents: full history + tool result as the next user turn
        contents = [
            genai.types.Content(
                role=msg["role"],
                parts=[genai.types.Part(text=msg["content"])],
            )
            for msg in history
        ]
        contents.append(
            genai.types.Content(
                role="user",
                parts=[genai.types.Part(text=f"[Tool result]\n{tool_result}")],
            )
        )

        # 4. Second LLM call to compose the final reply
        llm_client = LLMClient()
        allergy_str = ", ".join(allergies) if allergies else "None reported"
        follow_up = await llm_client.call(SYSTEM_PROMPT.format(allergies=allergy_str), contents)
        logger.info("LLM follow-up generated for user %s", user_id)

        # 5. Persist and send
        async with session_factory() as db:
            chat_repo = ChatRepository(db)
            await chat_repo.save_message(uid, "assistant", follow_up.text)

        WhatsappUtil.send_message_sync(phone_number, follow_up.text)
    finally:
        await engine.dispose()
