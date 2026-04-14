import logging
from datetime import date

from celery import Celery
from celery.schedules import crontab
from sqlalchemy import select

from app.config import settings
from app.database import get_sync_db
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
