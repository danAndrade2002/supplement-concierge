import logging

from google import genai

from app.config import settings

logger = logging.getLogger(__name__)


class LLMClient:

    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model = "gemini-2.0-flash"

    async def call(self, system_prompt: str, contents: list[genai.types.Content]) -> str:
        """Send contents to Gemini and return the raw text response."""
        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=genai.types.GenerateContentConfig(
                system_instruction=system_prompt,
            ),
        )
        return response.text.strip()
