"""Tests for TUI token status bar and streaming metrics capture."""

from types import SimpleNamespace

import pytest

from agno.agent import RunEvent

from src.core.agent_runner import AgentRunner
from src.interface.screens.chat_screen import ChatScreen
from src.storage import Message, Session, UsageMetrics


class _FakeConfig:
    def __init__(self, model: str = "openai:gpt-4o"):
        self.model = model
        self.name = "Test Agent"


class _FakeAgentInstance:
    def __init__(self, chunks=None):
        self._chunks = chunks or []

    async def run(self, messages):
        raise AssertionError("run() should not be called in this test")

    async def run_stream(self, messages, **kwargs):
        for chunk in self._chunks:
            yield chunk


class _FakeAgentManager:
    def __init__(self, agent_instance, agent_id: str = "agent-1"):
        self._agent_instance = agent_instance
        self._agent_id = agent_id
        self.mcp_manager = SimpleNamespace(resolve_tool_name=lambda raw: (None, None))

    def get_agent(self, agent_id: str):
        if agent_id == self._agent_id:
            return self._agent_instance
        return None

    async def load_agent(self, agent_id: str):
        return self.get_agent(agent_id)

    async def unload_all(self):
        return None

    def list_agents(self):
        return []


class _FakeConversationManager:
    def __init__(self, session: Session):
        self.session = session

    async def create_session(self, agent_id: str, title: str | None = None):
        self.session.agent_id = agent_id
        return self.session

    async def get_session(self, session_id: str):
        if session_id == self.session.id:
            return self.session
        return None

    async def add_message(self, session_id: str, role: str, content: str, metrics=None):
        message = Message(role=role, content=content, metrics=metrics)
        self.session.add_message(message)
        return message


@pytest.fixture
def empty_session():
    return Session(id="session-1", agent_id="agent-1", messages=[])


@pytest.fixture
def populated_session():
    return Session(
        id="session-1",
        agent_id="agent-1",
        messages=[
            Message(role="user", content="Hello agent"),
            Message(role="assistant", content="Hello user"),
        ],
    )


class TestAgentRunnerStreamingMetrics:
    async def test_send_message_streaming_persists_metrics_from_run_completed_event(self, empty_session):
        metrics = SimpleNamespace(
            input_tokens=120,
            output_tokens=45,
            total_tokens=165,
            cost=0.12,
            audio_input_tokens=0,
            audio_output_tokens=0,
            cache_read_tokens=0,
            cache_write_tokens=0,
            reasoning_tokens=3,
        )
        chunks = [
            SimpleNamespace(event=RunEvent.run_content.value, content="Hello "),
            SimpleNamespace(event=RunEvent.run_content.value, content="world"),
            SimpleNamespace(event=RunEvent.run_completed.value, metrics=metrics),
        ]
        runner = AgentRunner(
            agent_manager=_FakeAgentManager(_FakeAgentInstance(chunks)),
            conversation_manager=_FakeConversationManager(empty_session),
        )
        runner._current_agent_id = "agent-1"
        runner._current_session = empty_session

        response = await runner.send_message("Hi", stream_callback=lambda chunk: None)

        assert response == "Hello world"
        assert len(empty_session.messages) == 2
        assert empty_session.messages[-1].role == "assistant"
        assert empty_session.messages[-1].metrics is not None
        assert empty_session.messages[-1].metrics.input_tokens == 120
        assert empty_session.messages[-1].metrics.output_tokens == 45
        assert empty_session.messages[-1].metrics.total_tokens == 165

    async def test_send_message_streaming_emits_final_content_from_run_completed_when_no_run_content(self, empty_session):
        tool = SimpleNamespace(tool_name="get_skill_instructions", parameters={"skill_name": "explain-code"})
        chunks = [
            SimpleNamespace(event=RunEvent.tool_call_started.value, tool=tool),
            SimpleNamespace(event=RunEvent.tool_call_completed.value, tool=tool, content='{"skill_name":"explain-code"}'),
            SimpleNamespace(event=RunEvent.run_completed.value, content="`main.py` 是程式入口，負責初始化應用程式。", metrics=None),
        ]
        runner = AgentRunner(
            agent_manager=_FakeAgentManager(_FakeAgentInstance(chunks)),
            conversation_manager=_FakeConversationManager(empty_session),
        )
        runner._current_agent_id = "agent-1"
        runner._current_session = empty_session

        streamed_chunks: list[str] = []

        response = await runner.send_message("解釋 main.py", stream_callback=streamed_chunks.append)

        assert response == "`main.py` 是程式入口，負責初始化應用程式。"
        assert streamed_chunks == ["`main.py` 是程式入口，負責初始化應用程式。"]
        assert empty_session.messages[-1].content == "`main.py` 是程式入口，負責初始化應用程式。"


class TestAgentRunnerContextEstimation:
    async def test_estimate_context_tokens_counts_current_history_and_next_message(self, populated_session):
        runner = AgentRunner(
            agent_manager=_FakeAgentManager(_FakeAgentInstance([])),
            conversation_manager=_FakeConversationManager(populated_session),
        )
        runner._current_agent_id = "agent-1"
        runner._current_session = populated_session
        runner.config.get_agent = lambda agent_id: _FakeConfig()

        current_tokens = await runner.estimate_context_tokens()
        next_tokens = await runner.estimate_context_tokens("Please summarize this")

        assert current_tokens > 0
        assert next_tokens > current_tokens


class TestChatScreenTokenStatusFormatting:
    def test_format_token_status_renders_context_and_cumulative_metrics(self):
        metrics = UsageMetrics(input_tokens=1200, output_tokens=340, total_tokens=1540)

        status = ChatScreen.format_token_status(context_tokens=512, cumulative_metrics=metrics)

        assert status == "Context: 512 | Input: 1,200 | Output: 340 | Total: 1,540"

    def test_format_token_status_handles_missing_metrics(self):
        status = ChatScreen.format_token_status(context_tokens=None, cumulative_metrics=None)

        assert status == "Context: - | Input: 0 | Output: 0 | Total: 0"
