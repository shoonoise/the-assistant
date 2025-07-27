from __future__ import annotations

import json

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

DEFAULT_PROMPT = (
    "You are a helpful assistant that extracts a recurring schedule and the action "
    "to perform from a user instruction."
    " Respond ONLY with a JSON object using keys 'schedule' and 'instruction'."
)


class TaskParser:
    """Parse scheduling instructions using an LLM."""

    def __init__(self, model: ChatOpenAI | None = None) -> None:
        self.model = model or ChatOpenAI(model="gpt-4o-mini", temperature=0)  # type: ignore[unknown-argument]

    async def parse(self, text: str) -> tuple[str, str]:
        """Return schedule and instruction parsed from input."""
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", DEFAULT_PROMPT),
                ("human", "{text}"),
            ]
        )
        chain = prompt | self.model
        response = await chain.ainvoke({"text": text})
        content = getattr(response, "content", str(response))
        try:
            data = json.loads(content)
            schedule = str(data.get("schedule", ""))
            instruction = str(data.get("instruction", ""))
        except Exception:
            schedule = ""
            instruction = content
        return schedule, instruction
