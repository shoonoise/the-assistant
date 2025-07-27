import pytest
from langchain_core.language_models.fake_chat_models import FakeChatModel
from langchain_core.messages import AIMessage

from the_assistant.activities.messages_activities import (
    BriefingSummaryInput,
    build_briefing_summary,
)


@pytest.mark.asyncio
async def test_build_briefing_summary(monkeypatch):
    # Mock the create_react_agent function to avoid bind_tools issues
    class MockAgentExecutor:
        async def ainvoke(self, input_data, config=None):
            return {"messages": [AIMessage(content="Summary of data")]}

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
    monkeypatch.setattr(
        "the_assistant.integrations.llm.agent._default_model", lambda: llm
    )

    input_data = BriefingSummaryInput(user_id=1, data="example data")
    result = await build_briefing_summary(input_data)

    assert "Summary of data" in result
