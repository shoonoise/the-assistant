"""Simple LLM integration using LangChain."""

import logging
from dataclasses import dataclass

from langchain.callbacks.tracers.langchain import LangChainTracer
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langsmith import trace

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = DEFAULT_SYSTEM_PROMPT = (
    "You are a warm, smart, and human-like personal assistant helping the user manage daily life. "
    "You summarize only what matters, with a personal tone. Response limit: 4000 symbols. Respond should be on a user's language"
)


def _default_model() -> ChatOpenAI:
    """Create default ChatOpenAI model."""
    return ChatOpenAI(model="gpt-4o-mini", temperature=0.3)  # type: ignore[unknown-argument]


@dataclass
class Task:
    """Simple task for the LLM agent."""

    prompt: str
    data: str


class LLMAgent:
    """Minimal LangChain-based agent."""

    def __init__(
        self,
        system_prompt: str | None = None,
        model: ChatOpenAI | None = None,
        *,
        langsmith_project: str | None = None,
    ) -> None:
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        self.model = model or _default_model()
        self.langsmith_project = langsmith_project

    async def run(self, task: Task) -> str:
        """Execute a task and return LLM output."""
        prompt = ChatPromptTemplate.from_messages(
            [("system", self.system_prompt), ("human", task.prompt)]
        )
        chain = prompt | self.model | StrOutputParser()
        if self.langsmith_project:
            chain = chain.with_config(
                {
                    "callbacks": [LangChainTracer(project_name=self.langsmith_project)],
                    "run_name": "task",
                }
            )
        logger.info("Running LLM task with prompt %s", task.prompt)
        with trace("llm-task", project_name=self.langsmith_project, run_type="chain"):
            result = await chain.ainvoke({"data": task.data})
        return str(result)
