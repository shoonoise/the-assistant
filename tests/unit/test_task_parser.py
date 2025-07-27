import pytest
from langchain_core.language_models.fake_chat_models import FakeChatModel
from langchain_core.messages import AIMessage

from the_assistant.integrations.llm.task_parser import TaskParser


@pytest.mark.asyncio
async def test_task_parser(monkeypatch):
    class DummyModel(FakeChatModel):
        async def ainvoke(self, input_data, config=None):
            return AIMessage(
                content='{"schedule": "daily 6pm", "instruction": "send word"}'
            )

    model = DummyModel()

    parser = TaskParser(model=model)
    schedule, instruction = await parser.parse("every day at 6pm send me a word")

    assert schedule == "daily 6pm"
    assert instruction == "send word"
