import pytest
from langchain_core.language_models.fake import FakeListLLM

from the_assistant.activities.messages_activities import (
    BriefingSummaryInput,
    build_briefing_summary,
)


@pytest.mark.asyncio
async def test_build_briefing_summary(monkeypatch):
    llm = FakeListLLM(responses=["Summary"])

    monkeypatch.setattr(
        "the_assistant.integrations.llm.agent._default_model", lambda: llm
    )

    input_data = BriefingSummaryInput(user_id=1, data="example data")
    result = await build_briefing_summary(input_data)

    assert "Summary" in result
