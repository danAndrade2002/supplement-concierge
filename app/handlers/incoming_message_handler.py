import logging

from google import genai

from app.constants import SYSTEM_PROMPT
from app.database import async_session_factory
from app.llm.llm_client import LLMClient
from app.models.incoming_message import IncomingMessage
from app.models.llm_response import LLMResponse
from app.repositories.chat_repository import ChatRepository
from app.repositories.user_repository import UserRepository
from app.worker import run_search_and_reply

logger = logging.getLogger(__name__)


class IncomingMessageHandler:

    def __init__(self):
        self.llm_client = LLMClient()

    async def handle(self, incoming_message: IncomingMessage) -> str:
        async with async_session_factory() as db:
            user_repo = UserRepository(db)
            chat_repo = ChatRepository(db)
            user = await user_repo.get_or_create(incoming_message.phone_number)
            history = await chat_repo.load_history(user.id)

            await chat_repo.save_message(user.id, "user", incoming_message.text)

            try:
                reply = await self._process_with_llm(
                    phone_number=incoming_message.phone_number,
                    user_id=str(user.id),
                    allergies=user.allergies or [],
                    history=history,
                    user_message=incoming_message.text,
                )
                await chat_repo.save_message(user.id, "assistant", reply)
            except Exception:
                logger.exception("LLM call failed")
                reply = "Sorry, something went wrong. Please try again in a moment."

        return reply

    async def _process_with_llm(
        self,
        phone_number: str,
        user_id: str,
        allergies: list[str],
        history: list[dict],
        user_message: str,
    ) -> str:
        system_prompt = self._build_system_prompt(allergies)
        contents = self._build_contents(history, user_message)

        llm_response: LLMResponse = await self.llm_client.call(system_prompt, contents)

        logger.info("LLM requested action: %s", llm_response.action)

        if llm_response.action == "search":
            queries = llm_response.params.get("queries", [])
            exclude_ingredients = llm_response.params.get("exclude_ingredients", [])
            for query in queries:
                run_search_and_reply.delay(
                    phone_number=phone_number,
                    user_id=user_id,
                    query=query,
                    exclude_ingredients=exclude_ingredients,
                    llm_waiting_text=llm_response.text,
                    allergies=allergies,
                )
            logger.info("Enqueued %d search task(s) for user %s", len(queries), user_id)
        

        return llm_response.text

    def _build_system_prompt(self, allergies: list[str]) -> str:
        allergy_str = ", ".join(allergies) if allergies else "None reported"
        return SYSTEM_PROMPT.format(allergies=allergy_str)

    def _build_contents(self, history: list[dict], user_message: str) -> list[genai.types.Content]:
        contents = []
        for msg in history:
            contents.append(genai.types.Content(
                role=msg["role"],
                parts=[genai.types.Part(text=msg["content"])],
            ))
        contents.append(genai.types.Content(
            role="user",
            parts=[genai.types.Part(text=user_message)],
        ))
        return contents
