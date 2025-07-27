import pytest
from langchain_core.language_models.fake_chat_models import FakeChatModel
from langchain_core.messages import AIMessage

from the_assistant.integrations.llm import LLMAgent, Task


@pytest.mark.asyncio
async def test_llm_agent_runs(monkeypatch):
    # Mock the create_react_agent function to avoid bind_tools issues
    class MockAgentExecutor:
        async def ainvoke(self, input_data, config=None):
            return {"messages": [AIMessage(content="Hello World")]}

    def mock_create_react_agent(model, tools, prompt):
        return MockAgentExecutor()

    monkeypatch.setattr(
        "the_assistant.integrations.llm.agent.create_react_agent",
        mock_create_react_agent,
    )

    async def mock_get_default_tools(user_id):
        return []

    monkeypatch.setattr(
        "the_assistant.integrations.llm.agent.get_default_tools",
        mock_get_default_tools,
    )

    llm = FakeChatModel()
    agent = LLMAgent(system_prompt="sys", model=llm)
    task = Task(prompt="Say hi to {data}", data="World")
    result = await agent.run(task, user_id=1)
    assert "Hello World" in result


@pytest.mark.asyncio
async def test_llm_agent_langsmith(monkeypatch):
    tracer_called = False

    from langchain.callbacks.base import BaseCallbackHandler

    class DummyTracer(BaseCallbackHandler):
        def __init__(self, project_name: str | None = None) -> None:
            nonlocal tracer_called
            tracer_called = True
            super().__init__()

    # Mock the create_react_agent function to avoid bind_tools issues
    class MockAgentExecutor:
        async def ainvoke(self, input_data, config=None):
            return {"messages": [AIMessage(content="Hi there")]}

    def mock_create_react_agent(model, tools, prompt):
        return MockAgentExecutor()

    monkeypatch.setattr(
        "the_assistant.integrations.llm.agent.create_react_agent",
        mock_create_react_agent,
    )

    async def mock_get_default_tools(user_id):
        return []

    monkeypatch.setattr(
        "the_assistant.integrations.llm.agent.get_default_tools",
        mock_get_default_tools,
    )

    monkeypatch.setattr(
        "the_assistant.integrations.llm.agent.LangChainTracer",
        DummyTracer,
    )

    llm = FakeChatModel()
    agent = LLMAgent(system_prompt="sys", model=llm, langsmith_project="proj")
    task = Task(prompt="Say hi to {data}", data="World")
    result = await agent.run(task, user_id=1)

    assert tracer_called
    assert "Hi there" in result
