import logging

from twilio.rest import Client

from app.config import settings

logger = logging.getLogger(__name__)


class WhatsappUtil:

    @staticmethod
    def get_phone_number(from_: str) -> str:
        return from_.replace("whatsapp:", "")

    @staticmethod
    def send_message_sync(phone_number: str, body: str) -> None:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(
            from_=f"whatsapp:{settings.TWILIO_PHONE_NUMBER}",
            to=f"whatsapp:{phone_number}",
            body=body,
        )
        logger.info("Sent outbound WhatsApp message to %s", phone_number)
