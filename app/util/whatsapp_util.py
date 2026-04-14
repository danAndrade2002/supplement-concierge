import logging

logger = logging.getLogger(__name__)


class WhatsappUtil:
    
    @staticmethod
    def get_phone_number(from_: str) -> str:
        return from_.replace("whatsapp:", "")

    # TODO: implement a method to schedule a reminder
