from pydantic import BaseModel, Field


class IncomingMessage(BaseModel):
    """Parsed fields from a Meta webhook payload."""

    whatsapp_id: str = Field(..., description="The WhatsApp ID of the user who sent the message")
    text: str = Field(..., description="The message text received from the user")
