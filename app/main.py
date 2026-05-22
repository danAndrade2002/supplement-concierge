import logging
import uuid
from pathlib import Path

from app.logging_config import configure_logging, request_id_var

configure_logging()

import httpx
from fastapi import FastAPI, Form, Query, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.metrics import track_latency
from twilio.twiml.messaging_response import MessagingResponse

from app.config import settings
from app.handlers.incoming_message_handler import IncomingMessageHandler
from app.util.whatsapp_util import WhatsappUtil
from app.models.incoming_message import IncomingMessage

logger = logging.getLogger(__name__)

app = FastAPI(title="WhatsApp Supplement Assistant")

incoming_message_handler = IncomingMessageHandler()


@app.get("/metrics")
async def metrics():
    """Prometheus/VictoriaMetrics scrape endpoint."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/webhook")
@track_latency("webhook_response_time")
async def handle_webhook(
    Body: str = Form(""),
    From: str = Form(""),
    ProfileName: str = Form("User"),
):
    """Receive and process incoming WhatsApp messages from Twilio."""
    request_id_var.set(str(uuid.uuid4()))
    phone_number = WhatsappUtil.get_phone_number(From)
    logger.info(f"Received message from {ProfileName} ({phone_number}): {Body}")
    incoming_message = IncomingMessage(
        text=Body,
        phone_number=phone_number,
        user_name=ProfileName,
    )

    reply = await incoming_message_handler.handle(incoming_message)
    logger.info("Sending reply to %s: %s", From, reply)
    resp = MessagingResponse()
    resp.message(reply)

    return Response(content=str(resp), media_type="text/xml")


@app.get("/meli/callback")
async def meli_callback(code: str = Query(...)):
    """Receive the OAuth code from Mercado Livre and exchange it for tokens."""
    logger.info("MELI callback received (code=%s...)", code[:8])

    verifier_file = Path(__file__).parents[1] / ".meli_code_verifier"
    code_verifier = verifier_file.read_text().strip() if verifier_file.exists() else ""
    if code_verifier:
        logger.info("PKCE code_verifier found, will include in token request")
    else:
        logger.info("No PKCE code_verifier found, proceeding without it")

    payload = {
        "grant_type": "authorization_code",
        "client_id": settings.MELI_CLIENT_ID,
        "client_secret": settings.MELI_CLIENT_SECRET,
        "code": code,
        "redirect_uri": settings.MELI_REDIRECT_URI,
    }
    if code_verifier:
        payload["code_verifier"] = code_verifier

    logger.info("Exchanging authorization code for tokens")
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            "https://api.mercadolibre.com/oauth/token",
            data=payload,
            headers={"accept": "application/json", "content-type": "application/x-www-form-urlencoded"},
        )
    logger.info("Token exchange response: status=%d", response.status_code)

    if response.status_code != 200:
        logger.error("Token exchange failed: %s", response.text)
        return Response(
            content=f"Token exchange failed: {response.text}",
            status_code=response.status_code,
            media_type="text/plain",
        )

    data = response.json()
    access_token = data["access_token"]
    refresh_token = data.get("refresh_token", "")
    logger.info(
        "Tokens received (expires_in=%s, scope=%s)",
        data.get("expires_in"),
        data.get("scope"),
    )

    env_file = Path(__file__).parents[1] / ".env"
    try:
        text = env_file.read_text()
        for key, value in (("MELI_ACCESS_TOKEN", access_token), ("MELI_REFRESH_TOKEN", refresh_token)):
            if f"{key}=" in text:
                lines = text.splitlines()
                text = "\n".join(
                    f"{key}={value}" if line.startswith(f"{key}=") else line
                    for line in lines
                ) + "\n"
            else:
                text = text.rstrip("\n") + f"\n{key}={value}\n"
        env_file.write_text(text)
        logger.info("MELI tokens saved to .env")
    except Exception:
        logger.exception("Could not save MELI tokens to .env")

    return {
        "message": "Mercado Livre authenticated successfully! Tokens saved to .env.",
        "access_token": access_token[:20] + "...",
        "expires_in": data.get("expires_in"),
        "scope": data.get("scope"),
    }
