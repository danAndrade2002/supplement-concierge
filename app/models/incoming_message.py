from pydantic import BaseModel, Field


class IncomingMessage(BaseModel):
    """Parsed fields from a Meta webhook payload."""

    phone_number: str = Field(..., description="The phone number of the user who sent the message")
    user_name: str = Field(..., description="The name of the user who sent the message")
    text: str = Field(..., description="The message text received from the user")
