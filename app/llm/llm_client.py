import json
import logging

from google import genai

from app.config import settings

from app.models.llm_response import LLMResponse

logger = logging.getLogger(__name__)

class LLMClient:

    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model = "gemini-2.5-flash-lite"

    async def call(self, system_prompt: str, contents: list[genai.types.Content]) -> LLMResponse:
        """Send contents to Gemini and return the raw text response."""
        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=self._build_config(system_prompt),
        )
        return LLMResponse(**json.loads(response.text.strip()))
    
    def _build_config(self, system_prompt: str) -> genai.types.GenerateContentConfig:
        return genai.types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_json_schema=LLMResponse.model_json_schema(),
        )