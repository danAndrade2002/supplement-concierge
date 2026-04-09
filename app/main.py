import logging

from fastapi import FastAPI, Query, Request, Response

from app.config import settings
from app.handlers.incoming_message_handler import IncomingMessageHandler
from app.util.whatsapp_util import WhatsappUtil

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="WhatsApp Supplement Assistant")

incoming_message_handler = IncomingMessageHandler()


@app.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """Meta webhook verification handshake."""
    if hub_mode == "subscribe" and hub_verify_token == settings.META_VERIFY_TOKEN:
        return Response(content=hub_challenge, media_type="text/plain")
    return Response(status_code=403)


@app.post("/webhook")
async def handle_webhook(request: Request):
    """Receive and process incoming WhatsApp messages."""
    payload = await request.json()

    incoming_message = WhatsappUtil.parse_message(payload)
    if incoming_message is None:
        return Response(status_code=200)

    reply = await incoming_message_handler.handle(incoming_message)
    await WhatsappUtil.send_message(incoming_message.whatsapp_id, reply)
    return Response(status_code=200)
