import pytest
from langchain_core.language_models.fake import FakeListLLM

from the_assistant.integrations.llm import LLMAgent, Task


@pytest.mark.asyncio
async def test_llm_agent_runs():
    llm = FakeListLLM(responses=["Hello"])
    agent = LLMAgent(system_prompt="sys", model=llm)
    task = Task(prompt="Say hi to {data}", data="World")
    result = await agent.run(task)
    assert "Hello" in result


@pytest.mark.asyncio
async def test_llm_agent_langsmith(monkeypatch):
    llm = FakeListLLM(responses=["Hi"])
    tracer_called = False

    from langchain.callbacks.base import BaseCallbackHandler

    class DummyTracer(BaseCallbackHandler):
        def __init__(self, project_name: str | None = None) -> None:
            nonlocal tracer_called
            tracer_called = True
            super().__init__()

    monkeypatch.setattr(
        "the_assistant.integrations.llm.agent.LangChainTracer",
        DummyTracer,
    )

    agent = LLMAgent(system_prompt="sys", model=llm, langsmith_project="proj")
    task = Task(prompt="Say hi to {data}", data="World")
    result = await agent.run(task)

    assert tracer_called
    assert "Hi" in result
