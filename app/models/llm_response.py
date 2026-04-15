from pydantic import BaseModel
from typing import Optional

class LLMResponse(BaseModel):
    text: Optional[str] = None
    action: Optional[str] = None
    params: Optional[dict] = None

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "action": self.action,
            "params": self.params,
        }