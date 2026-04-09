import logging

import httpx

from app.config import settings
from app.models.incoming_message import IncomingMessage

logger = logging.getLogger(__name__)

META_API_BASE = "https://graph.facebook.com/v21.0"


class WhatsappUtil:
    @staticmethod
    def parse_message(payload: dict) -> IncomingMessage | None:
        """Extract sender phone and message text from a WhatsApp message payload.

        Returns None for non-message events (status updates, read receipts, etc.).
        """
        try:
            entry = payload["entry"][0]
            change = entry["changes"][0]
            value = change["value"]
            message = value["messages"][0]
            whatsapp_id = message["from"]
            message_text = message.get("text", {}).get("body", "")
            if not message_text:
                return None
            return IncomingMessage(whatsapp_id=whatsapp_id, message_text=message_text)
        except (KeyError, IndexError):
            return None

    @staticmethod
    async def send_message(to: str, body: str) -> None:
        """Send a text message via the Meta WhatsApp Cloud API."""
        url = f"{META_API_BASE}/{settings.META_PHONE_NUMBER_ID}/messages"
        headers = {
            "Authorization": f"Bearer {settings.META_API_TOKEN}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": body},
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                logger.error("Meta API error %s: %s", resp.status_code, resp.text)

    @staticmethod
    def send_message_sync(to: str, body: str) -> None:
        """Synchronous variant for use in Celery tasks."""
        url = f"{META_API_BASE}/{settings.META_PHONE_NUMBER_ID}/messages"
        headers = {
            "Authorization": f"Bearer {settings.META_API_TOKEN}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": body},
        }
        with httpx.Client() as client:
            resp = client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                logger.error("Meta API error %s: %s", resp.status_code, resp.text)
