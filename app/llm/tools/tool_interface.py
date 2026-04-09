import abc
from typing import Any

class ITool(abc.ABC):
    """Interface that all LLM tools must implement."""

    @abc.abstractmethod
    async def execute(self, params: dict[str, Any]) -> str:
        ...
