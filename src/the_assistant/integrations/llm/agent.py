"""Simple LLM integration using LangChain with iterative tool usage."""

import logging
from dataclasses import dataclass

from langchain.callbacks.tracers.langchain import LangChainTracer
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langsmith import trace

from the_assistant.integrations.agent_tools import get_default_tools

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = (
    "You are a warm, smart, human‑like personal assistant who helps the user manage daily life. "
    "Summarise only what matters in a friendly, personal tone. "
    "Maximum length: 4 000 characters. "
    "Write in the user’s language. "
    "Output must be valid HTML using ONLY these tags: "
    "<b>, <strong>, <i>, <em>, <u>, <ins>, <s>, <strike>, <del>, "
    '<a href="URL">, <code>, <pre>, <span class="tg-spoiler">, <tg-spoiler>. '
    "Never use Markdown syntax (e.g. **bold**, _italics_, ## headings, <p> tags, or <br>). "
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
    """LangChain-based agent with iterative tool usage."""

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

    async def run(self, task: Task, user_id: int) -> str:
        """Execute a task with iterative tool usage and return final output."""
        # Get tools for this user
        tools = await get_default_tools(user_id)

        # Create the full prompt by combining system prompt, data context, and user prompt
        full_prompt = task.prompt
        if task.data:
            # Replace {data} placeholder in the prompt with actual data
            full_prompt = task.prompt.replace("{data}", task.data)

        # Create prompt template for the agent (simple template without variables in system message)
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", self.system_prompt),
                ("placeholder", "{messages}"),
            ]
        )

        # Create ReAct agent with tools
        agent_executor = create_react_agent(self.model, tools, prompt=prompt)

        # Configure callbacks if LangSmith project is specified
        config = {}
        if self.langsmith_project:
            config = {
                "callbacks": [LangChainTracer(project_name=self.langsmith_project)],
                "run_name": "agent-task",
            }

        logger.info(
            "Running iterative agent task with prompt: %s",
            full_prompt[:200] + "..." if len(full_prompt) > 200 else full_prompt,
        )

        with trace("agent-task", project_name=self.langsmith_project, run_type="chain"):
            # Run the agent with the full prompt
            result = await agent_executor.ainvoke(
                {"messages": [HumanMessage(content=full_prompt)]}, config=config
            )

            # Extract the final message content
            final_message = result["messages"][-1]
            return str(final_message.content)
