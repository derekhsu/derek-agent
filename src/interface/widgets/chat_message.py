"""Chat message widget for Derek Agent Runner TUI."""

from textual.containers import Horizontal, Vertical
from textual.widgets import Label, Markdown, Static

THINKING_PLACEHOLDER = "思考中..."


class ChatMessage(Vertical):
    """A single chat message widget."""

    DEFAULT_CSS = """
    ChatMessage {
        width: 100%;
        height: auto;
        margin: 0;
    }

    ChatMessage.user {
        align: right middle;
    }

    ChatMessage.assistant {
        align: left middle;
    }

    ChatMessage Horizontal {
        width: 100%;
        height: auto;
    }

    ChatMessage .sender-label {
        color: $text-muted;
        text-style: bold;
        width: auto;
        height: auto;
        margin: 0;
        padding: 0 1;
    }

    ChatMessage .message-content {
        width: 100%;
        height: auto;
        margin: 0;
        padding: 0 1 0 1;
    }

    ChatMessage Markdown.message-content {
        padding: 0 1 0 1;
    }

    ChatMessage Markdown.message-content > MarkdownParagraph {
        margin: 0;
    }

    ChatMessage.thinking .message-content {
        color: $text-muted;
        text-style: dim italic;
    }

    ChatMessage.mcp-activity {
        margin: 1 0;
    }

    ChatMessage.mcp-activity .sender-label {
        color: $accent;
        text-style: bold;
    }

    ChatMessage.mcp-activity .message-content {
        color: $accent;
        text-style: dim;
    }

    ChatMessage.mcp-activity.start .message-content {
        color: $primary;
    }

    ChatMessage.mcp-activity.success .message-content {
        color: $success;
    }

    ChatMessage.mcp-activity.error .message-content {
        color: $error;
    }
    """

    def __init__(self, role: str, content: str, timestamp: str | None = None, mcp_phase: str | None = None):
        """Initialize chat message.

        Args:
            role: Message role (user/assistant/system).
            content: Message content.
            timestamp: Optional timestamp string.
            mcp_phase: Optional MCP activity phase (start/success/error).
        """
        super().__init__()
        self.role = role
        self.content = content
        self.timestamp = timestamp
        self.mcp_phase = mcp_phase
        self._first_update = True

    def compose(self):
        """Compose the widget."""
        self.add_class(self.role)

        if self.content == THINKING_PLACEHOLDER:
            self.add_class("thinking")

        # Handle MCP activity messages
        if self.role == "system" and self.mcp_phase:
            self.add_class("mcp-activity")
            self.add_class(self.mcp_phase)
            sender = "MCP"
        elif self.role == "user":
            sender = "你"
        elif self.role == "assistant":
            sender = "AI"
        else:
            sender = "系統"

        with Horizontal():
            yield Label(sender, classes="sender-label")

        if self.role == "assistant":
            yield Markdown(self.content, classes="message-content")
        else:
            yield Static(self.content, classes="message-content")

    def update_content(self, content: str) -> None:
        """Update message content (for streaming)."""
        self.content = content

        if self._first_update and self.has_class("thinking"):
            self.remove_class("thinking")
            self._first_update = False

        if self.role == "assistant":
            markdown = self.query_one(Markdown)
            markdown.update(content)
        else:
            static = self.query_one(Static)
            static.update(content)
