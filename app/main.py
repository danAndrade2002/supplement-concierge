import logging

from fastapi import FastAPI, Form, Response
from twilio.twiml.messaging_response import MessagingResponse

from app.config import settings
from app.handlers.incoming_message_handler import IncomingMessageHandler
from app.util.whatsapp_util import WhatsappUtil

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="WhatsApp Supplement Assistant")

incoming_message_handler = IncomingMessageHandler()


@app.post("/webhook")
async def handle_webhook(
    Body: str = Form(""),
    From: str = Form(""),
    ProfileName: str = Form("User"),
):
    """Receive and process incoming WhatsApp messages from Twilio."""
    logger.info(f"Received message from {ProfileName} ({From}): {Body}")


    # reply = await incoming_message_handler.handle(Body)
    reply = await incoming_message_handler.handle_twilio_migration(Body)
    logger.info("Sending reply to %s: %s", From, reply)
    resp = MessagingResponse()
    resp.message(reply)
    
    return Response(content=str(resp), media_type="text/xml")

