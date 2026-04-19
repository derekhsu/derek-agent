"""Input bar widget for Derek Agent Runner TUI."""

import asyncio

from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Button

from ..commands import get_command_registry, register_all_commands
from .enhanced_input import EnhancedInput
from .slash_command_popup import SlashCommandPopup


class InputBar(Vertical):
    """Input bar with text input, send button and slash command popup."""

    DEFAULT_CSS = """
    InputBar {
        width: 100%;
        height: auto;
        dock: bottom;
        padding: 0;
    }

    InputBar #popup-area {
        width: 100%;
        height: auto;
    }

    InputBar #input-row {
        width: 100%;
        height: auto;
        padding: 0 1;
    }

    InputBar EnhancedInput {
        width: 1fr;
        height: 3;
    }

    InputBar Button {
        width: auto;
        min-width: 8;
    }

    InputBar SlashCommandPopup {
        width: 40;
        height: auto;
        max-height: 15;
        background: $surface;
        border: solid $primary;
        dock: none;
        margin-left: 1;
    }
    """

    is_generating = reactive(False)

    def __init__(self):
        """Initialize input bar."""
        super().__init__()
        self._pending_content = ""
        self._slash_mode = False
        self._popup: SlashCommandPopup | None = None
        register_all_commands()
        self._registry = get_command_registry()

    def compose(self):
        """Compose the widget."""
        with Vertical(id="popup-area"):
            pass
        with Horizontal(id="input-row"):
            yield EnhancedInput(
                registry=self._registry,
                placeholder="輸入訊息... (Enter 發送, / 指令)",
                id="message-input",
            )
            yield Button("發送", id="send-btn", variant="primary")

    def on_mount(self):
        """Called when widget is mounted."""
        self.update_button_state()

    # --- Slash command popup management ---

    def on_input_changed(self, event):
        """Handle input changes to track slash mode."""
        if event.input.id != "message-input":
            return
        value = event.value
        if value.startswith("/"):
            prefix = value[1:].split(" ", 1)[0]
            if not self._slash_mode:
                self._slash_mode = True
                self._show_popup(prefix)
            else:
                self._update_popup(prefix)
        else:
            if self._slash_mode:
                self._slash_mode = False
                self._hide_popup()

    def on_key(self, event):
        """Intercept arrow keys for popup navigation."""
        if not self._popup:
            return
        if event.key == "down":
            event.stop()
            self._popup.select_next()
        elif event.key == "up":
            event.stop()
            self._popup.select_previous()
        elif event.key == "escape":
            event.stop()
            self._hide_popup()
        elif event.key == "tab":
            event.stop()
            self._complete_command()

    def _show_popup(self, prefix: str):
        """Mount popup into popup-area."""
        popup_area = self.query_one("#popup-area", Vertical)
        self._popup = SlashCommandPopup(self._registry, prefix)
        popup_area.mount(self._popup)

    def _update_popup(self, prefix: str):
        """Update popup prefix."""
        if self._popup:
            self._popup.prefix = prefix
            self._popup.update_commands()

    def _hide_popup(self):
        """Remove popup."""
        if self._popup:
            self._popup.remove()
            self._popup = None
        self._slash_mode = False

    def _complete_command(self):
        """Tab-complete selected command."""
        if not self._popup:
            return
        name = self._popup.get_selected_command()
        if name:
            inp = self.query_one("#message-input", EnhancedInput)
            inp.value = f"/{name} "
            inp.cursor_position = len(inp.value)
            self._update_popup("")

    def on_slash_command_popup_command_selected(self, event: SlashCommandPopup.CommandSelected):
        """Handle popup item click."""
        self._execute_slash_command(event.command_name, [])
        self._hide_popup()

    # --- Command execution ---

    def _execute_slash_command(self, command_name: str, args: list[str]):
        """Execute a slash command asynchronously."""
        async def run_command():
            from ..app import DerekAgentApp
            app = self.app
            runner = getattr(app, "runner", None) if isinstance(app, DerekAgentApp) else None
            result = await self._registry.execute(command_name, args, app=app, runner=runner)
            if result.message:
                msg_cls = self.SystemMessage if result.success else self.ErrorMessage
                self.post_message(msg_cls(result.message))

        asyncio.create_task(run_command())
        inp = self.query_one("#message-input", EnhancedInput)
        inp.value = ""
        self._pending_content = ""

    # --- Input submission ---

    def on_input_submitted(self, event):
        """Handle Enter key in input."""
        if event.input.id != "message-input":
            return
        inp = self.query_one("#message-input", EnhancedInput)
        if self._popup:
            # If popup is open, Enter selects current item
            name = self._popup.get_selected_command()
            self._hide_popup()
            if name:
                self._execute_slash_command(name, [])
            elif inp.is_slash_command():
                cmd_name, args = inp.parse_slash_command()
                if cmd_name:
                    self._execute_slash_command(cmd_name, args)
        elif inp.is_slash_command():
            cmd_name, args = inp.parse_slash_command()
            if cmd_name:
                self._execute_slash_command(cmd_name, args)
        else:
            self.send_message()

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button press."""
        if event.button.id == "send-btn":
            if self.is_generating:
                self.action_stop()
            else:
                self.send_message()

    def send_message(self):
        """Send the current message."""
        inp = self.query_one("#message-input", EnhancedInput)
        message = inp.value.strip()
        if message and not self.is_generating:
            inp.value = ""
            self._pending_content = ""
            self.post_message(self.MessageSent(message))

    def action_stop(self):
        """Stop generation."""
        self.post_message(self.GenerationStopped())

    def set_generating(self, generating: bool):
        """Set generation state."""
        self.is_generating = generating
        self.update_button_state()

    def update_button_state(self):
        """Update button label based on state."""
        button = self.query_one("#send-btn", Button)
        if self.is_generating:
            button.label = "停止"
            button.variant = "error"
        else:
            button.label = "發送"
            button.variant = "primary"

    def focus_input(self):
        """Focus the input field."""
        self.query_one("#message-input", EnhancedInput).focus()

    class MessageSent(Message):
        """Message sent event."""

        def __init__(self, content: str):
            self.content = content
            super().__init__()

    class GenerationStopped(Message):
        """Generation stopped event."""

        def __init__(self):
            super().__init__()

    class SystemMessage(Message):
        """System message for command results."""

        def __init__(self, content: str):
            self.content = content
            super().__init__()

    class ErrorMessage(Message):
        """Error message for command failures."""

        def __init__(self, content: str):
            self.content = content
            super().__init__()
