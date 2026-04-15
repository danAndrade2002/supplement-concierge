import json
import logging
import uuid

from google import genai
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import SYSTEM_PROMPT
from app.database import async_session_factory
from app.llm.llm_client import LLMClient
from app.llm.tools.tool_factory import ToolFactory
from app.models.incoming_message import IncomingMessage
from app.models.llm_response import LLMResponse
from app.repositories.chat_repository import ChatRepository
from app.repositories.user_repository import UserRepository

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
                tool_factory = ToolFactory(db, user.id)
                reply = await self._process_with_llm(
                    tool_factory, user.allergies or [], history, incoming_message.text
                )
                await chat_repo.save_message(user.id, "assistant", reply)
            except Exception:
                logger.exception("LLM call failed")
                reply = "Sorry, something went wrong. Please try again in a moment."

        return reply

    # TODO: Improve how we process the LLM response and call the tool if needed.
    async def _process_with_llm(
        self, tool_factory: ToolFactory, allergies: list[str],
        history: list[dict], user_message: str,
    ) -> str:
        system_prompt = self._build_system_prompt(allergies)
        contents = self._build_contents(history, user_message)

        llm_response: LLMResponse = await self.llm_client.call(system_prompt, contents)

        if llm_response.action is None:
            logger.info(f"No tool calling needed, returning response: {llm_response.text}")
            return llm_response.text

        logger.info(f"LLM requested action: {llm_response.action}")
        
        tool = tool_factory.build_tool(llm_response.action)
        tool_result = await tool.execute(llm_response.params)
        contents.append(
            genai.types.Content(
                role="model",
                parts=[genai.types.Part(text=llm_response.text)],
            )
        )
        contents.append(
            genai.types.Content(
                role="user",
                parts=[genai.types.Part(text=f"[Tool result]\n{tool_result}")],
            )
        )
        follow_up = await self.llm_client.call(system_prompt, contents)
        return follow_up.text

    def _build_system_prompt(self,allergies: list[str]) -> str:
        allergy_str = ", ".join(allergies) if allergies else "None reported"
        return SYSTEM_PROMPT.format(allergies=allergy_str)

    def _build_contents(self, history: list[dict], user_message: str) -> list[genai.types.Content]:
        contents = []
        for msg in history:
            contents.append(
                genai.types.Content(
                    role=msg["role"],
                    parts=[genai.types.Part(text=msg["content"])],
                )
            )
        contents.append(
            genai.types.Content(
                role="user",
                parts=[genai.types.Part(text=user_message)],
            )
        )
        return contents
