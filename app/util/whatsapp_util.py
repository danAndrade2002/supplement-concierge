# TODO: Review if we will really need this

import logging

from twilio.rest import Client

from app.config import settings
from app.models.incoming_message import IncomingMessage

logger = logging.getLogger(__name__)

_twilio_client: Client | None = None


def _get_twilio_client() -> Client:
    global _twilio_client
    if _twilio_client is None:
        _twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    return _twilio_client


class WhatsappUtil:

    @staticmethod
    def parse_message(form_data: dict) -> IncomingMessage | None:
        """Extract sender phone and message text from Twilio's form-encoded webhook.

        Returns None for non-message events (status callbacks, media-only, etc.).
        """
        body = form_data.get("Body", "").strip()
        sender = form_data.get("From", "")
        if not body or not sender:
            return None

        whatsapp_id = sender.replace("whatsapp:", "")
        return IncomingMessage(whatsapp_id=whatsapp_id, text=body)

    @staticmethod
    def send_message(to: str, body: str) -> None:
        """Send a WhatsApp message via the Twilio SDK."""
        client = _get_twilio_client()
        to_clean = to.replace("whatsapp:", "")
        if not to_clean.startswith("+"):
            to_clean = f"+{to_clean}"
        to_addr = f"whatsapp:{to_clean}"
        from_addr = f"whatsapp:{settings.TWILIO_PHONE_NUMBER}"

        try:
            message = client.messages.create(
                body=body,
                from_=from_addr,
                to=to_addr,
            )
            logger.info("Message sent, SID: %s", message.sid)
        except Exception:
            logger.exception("Failed to send message to %s", to)

    @staticmethod
    def send_message_sync(to: str, body: str) -> None:
        """Synchronous variant for Celery tasks (Twilio SDK is already sync)."""
        WhatsappUtil.send_message(to, body)
