from __future__ import annotations

import json
from datetime import datetime
from json import JSONDecodeError

from dateutil.parser import parse as parse_date
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

DEFAULT_PROMPT = (
    "You are a helpful assistant that extracts an event date/time and a short description from a user instruction."
    " Respond ONLY with a JSON object using keys 'date' and 'description'."
)


class CountdownParser:
    """Parse countdown instructions using an LLM."""

    def __init__(self, model: ChatOpenAI | None = None) -> None:
        self.model = model or ChatOpenAI(model="gpt-4o-mini", temperature=0)  # type: ignore[unknown-argument]

    async def parse(self, text: str) -> tuple[datetime | None, str]:
        """Return event_time and description parsed from input."""
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
            date_str = data.get("date")
            description = str(data.get("description", ""))
            event_time = parse_date(date_str) if date_str else None
        except (JSONDecodeError, ValueError):
            event_time = None
            description = content
        return event_time, description
