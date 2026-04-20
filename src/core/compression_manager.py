"""Context compression manager for Derek Agent Runner."""

import threading
from typing import TYPE_CHECKING

from agno.utils.log import logger
from agno.utils.tokens import count_text_tokens

from ..storage import Message, Session, UsageMetrics
from .providers import get_model_context_window

if TYPE_CHECKING:
    from .agent_manager import AgentInstance


# Summary prompt template in Traditional Chinese
SUMMARY_PROMPT_TEMPLATE = """請將以下對話內容整理成一份簡潔的摘要。摘要應該包含：

1. 主題：這次對話的核心主題是什麼
2. 關鍵決策：已經做出或討論過的重要決定
3. 待辦事項：還需要處理或確認的事項
4. 重要資訊：需要記住的核心資訊

對話內容：
{conversation}

請用繁體中文撰寫摘要，盡量簡潔但保留關鍵細節："""


class CompressionManager:
    """Manages context compression for conversations."""

    def __init__(self, agent_instance: "AgentInstance | None" = None):
        """Initialize compression manager.

        Args:
            agent_instance: Optional agent instance for running compression.
        """
        self.agent_instance = agent_instance
        self._lock = threading.Lock()

    def set_agent_instance(self, agent_instance: "AgentInstance") -> None:
        """Set the agent instance (thread-safe).
        
        Args:
            agent_instance: The agent instance to use for compression.
        """
        with self._lock:
            self.agent_instance = agent_instance

    def get_agent_instance(self) -> "AgentInstance | None":
        """Get the agent instance (thread-safe).
        
        Returns:
            The current agent instance or None.
        """
        with self._lock:
            return self.agent_instance

    def get_context_window(self, model_id: str, provider: str | None = None) -> int:
        """Get context window size for a model.

        Args:
            model_id: Model identifier.
            provider: Optional provider name.

        Returns:
            Context window size in tokens.
        """
        return get_model_context_window(model_id, provider)

    def estimate_context_tokens(
        self,
        session: Session,
        model_id: str,
        system_prompt: str = "",
        pending_message: str | None = None,
    ) -> int:
        """Estimate total context tokens for a session.

        Args:
            session: Conversation session.
            model_id: Model identifier for token counting.
            system_prompt: System prompt to include in estimation.
            pending_message: Optional pending message to include.

        Returns:
            Estimated token count.
        """
        total = 0

        # Count system prompt tokens
        if system_prompt:
            total += count_text_tokens(f"system: {system_prompt}", model_id)

        # Count message tokens
        for msg in session.messages:
            if msg.role in ("user", "assistant"):
                total += count_text_tokens(f"{msg.role}: {msg.content}", model_id)

        # Count pending message if provided
        if pending_message:
            total += count_text_tokens(f"user: {pending_message}", model_id)

        return total

    def should_compress(
        self,
        session: Session,
        model_id: str,
        system_prompt: str = "",
        pending_message: str | None = None,
        threshold_percent: int = 50,
    ) -> tuple[bool, int, int]:
        """Check if conversation should be compressed.

        Args:
            session: Conversation session.
            model_id: Model identifier.
            system_prompt: System prompt to include.
            pending_message: Optional pending message.
            threshold_percent: Threshold percentage (1-100).

        Returns:
            Tuple of (should_compress, current_tokens, threshold_tokens).
        """
        context_window = self.get_context_window(model_id)
        current_tokens = self.estimate_context_tokens(
            session, model_id, system_prompt, pending_message
        )
        threshold_tokens = int(context_window * (threshold_percent / 100))

        should_compress = current_tokens >= threshold_tokens

        if should_compress:
            logger.debug(
                f"Compression triggered: {current_tokens} tokens >= "
                f"{threshold_tokens} threshold ({threshold_percent}% of {context_window})"
            )

        return should_compress, current_tokens, threshold_tokens

    async def compress_session(
        self,
        session: Session,
        model_id: str,
        summary_model: str | None = None,
        max_summary_tokens: int = 500,
    ) -> tuple[str, UsageMetrics | None]:
        """Compress a session by generating a summary.

        Args:
            session: Conversation session to compress.
            model_id: Current model identifier.
            summary_model: Optional model for summarization (None uses current).
            max_summary_tokens: Maximum tokens for summary.

        Returns:
            Tuple of (summary_text, metrics).
        """
        # Thread-safe access to agent instance
        with self._lock:
            agent_instance = self.agent_instance
            
        if not agent_instance:
            raise RuntimeError("Agent instance required for compression")

        # Build conversation text
        conversation_parts = []
        for msg in session.messages:
            if msg.role == "user":
                conversation_parts.append(f"使用者：{msg.content}")
            elif msg.role == "assistant":
                conversation_parts.append(f"助手：{msg.content}")

        conversation_text = "\n\n".join(conversation_parts)

        # Build summary prompt
        summary_prompt = SUMMARY_PROMPT_TEMPLATE.format(conversation=conversation_text)

        # Use summary model if specified, otherwise use current agent
        try:
            if summary_model and summary_model != model_id:
                # Create a temporary agent with summary model
                from .agent_manager import parse_model_string, create_model

                provider, model_name = parse_model_string(summary_model)
                summary_agent_model = create_model(provider, model_name)

                # Run summarization with summary model
                from agno.agent import Agent

                temp_agent = Agent(
                    model=summary_agent_model,
                    instructions="你是一個專業的對話摘要助手。請用繁體中文生成簡潔但完整的摘要。",
                    markdown=True,
                )
                response = await temp_agent.arun(summary_prompt)
            else:
                # Use current agent for summarization
                response = await agent_instance.run(summary_prompt)

            summary_text = getattr(response, "content", str(response))

            # Extract metrics if available
            metrics = None
            if hasattr(response, "metrics") and response.metrics:
                metrics = UsageMetrics(
                    input_tokens=getattr(response.metrics, "input_tokens", 0),
                    output_tokens=getattr(response.metrics, "output_tokens", 0),
                    total_tokens=getattr(response.metrics, "total_tokens", 0),
                )

            logger.info(f"Session compressed: {len(session.messages)} messages summarized")
            return summary_text, metrics

        except Exception as e:
            logger.error(f"Failed to compress session: {e}")
            raise

    def build_compressed_messages(
        self,
        session: Session,
        summary: str,
    ) -> list[dict]:
        """Build message list with summary replacing archived messages.

        Args:
            session: Original session.
            summary: Generated summary text.

        Returns:
            List of message dicts for agent context.
        """
        messages = []

        # Add summary as system message
        messages.append({
            "role": "system",
            "content": f"【對話摘要】\n{summary}\n\n以上是你與使用者之前的對話摘要。請基於此摘要繼續協助使用者。"
        })

        return messages
