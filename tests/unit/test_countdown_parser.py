import pytest
from langchain_core.language_models.fake_chat_models import FakeChatModel
from langchain_core.messages import AIMessage

from the_assistant.integrations.llm.countdown_parser import CountdownParser


@pytest.mark.asyncio
async def test_countdown_parser(monkeypatch):
    class DummyModel(FakeChatModel):
        async def ainvoke(self, input_data, config=None):
            return AIMessage(content='{"date": "2025-01-01", "description": "party"}')

    model = DummyModel()
    parser = CountdownParser(model=model)
    event_time, description = await parser.parse("party on 2025-01-01")

    assert event_time.year == 2025
    assert description == "party"
