"""tui/screens/api_key.py — API key entry screen (Full Replication mode only)."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, Label, Static
from textual.containers import Center, Horizontal, Vertical

from tui.clipboard import get_system_clipboard
from tui.config import MODELS


_PROVIDER_LINKS = {
    "openai":   "https://platform.openai.com/api-keys",
    "gemini":   "https://aistudio.google.com/app/apikey",
    "deepseek": "https://platform.deepseek.com/api_keys",
}

_PROVIDER_NAMES = {
    "openai":   "OpenAI",
    "gemini":   "Google GenAI",
    "deepseek": "DeepSeek",
}


class ApiKeyScreen(Screen):
    """Collect and validate the LLM API key for Step 1."""

    BINDINGS = [
        ("ctrl+v", "paste_clipboard", "Paste"),
        ("shift+insert", "paste_clipboard", "Paste"),
    ]

    CSS = """
    ApiKeyScreen {
        align: center middle;
        overflow-y: auto;
        background: #000000;
        color: #ffffff;
    }
    #key-box {
        width: 72;
        height: auto;
        padding: 1 3;
        border: solid #ffffff;
        background: #000000;
    }
    Input {
        margin: 1 0;
        background: #000000;
        color: #ffffff;
        border: solid #ffffff;
    }
    #paste-row {
        margin: 0 0 1 0;
        height: auto;
        align: center middle;
    }
    #paste-row Button {
        margin: 0 1;
        min-width: 20;
    }
    #note {
        color: #888888;
        margin-top: 1;
    }
    #btn-row {
        margin-top: 1;
        height: auto;
        align: center middle;
    }
    #btn-row Button {
        margin: 0 2;
        min-width: 16;
    }
    """

    def compose(self) -> ComposeResult:
        model_key = getattr(self.app, "selected_model", "")
        provider  = MODELS.get(model_key, {}).get("provider", "openai")
        pname     = _PROVIDER_NAMES.get(provider, provider)
        plink     = _PROVIDER_LINKS.get(provider, "")

        yield Header(show_clock=False)
        with Center():
            with Vertical(id="key-box"):
                yield Static(
                    "[bold]Step 3 of 4: API Key[/]\n\n"
                    f"Enter your [bold]{pname}[/] API key.\n"
                    f"[dim]Reference: {plink}[/]\n\n"
                    "[dim]Note: Step 1 calls the LLM API for each question in the dataset.\n"
                    "This requires network connectivity and API quota.[/]\n"
                )
                yield Input(
                    placeholder="Paste or type your API key here...",
                    password=True,
                    id="api-key-input",
                )
                with Horizontal(id="paste-row"):
                    yield Button("Paste from Clipboard", id="btn-paste")
                    yield Button("Clear", id="btn-clear")
                yield Static(
                    "[dim]Tip: Press Ctrl+V, Shift+Insert, or click 'Paste from Clipboard'.[/]\n"
                    "[dim]The key is kept only in memory for this run and never stored to disk.[/]",
                    id="note",
                )
                with Horizontal(id="btn-row"):
                    yield Button("Back", id="btn-back")
                    yield Button("Next", id="btn-next")
        yield Footer()

    def on_mount(self) -> None:
        stored = getattr(self.app, "api_key", "")
        inp = self.query_one("#api-key-input", Input)
        if stored:
            inp.value = stored
        inp.focus()

    def action_paste_clipboard(self) -> None:
        self._paste_from_clipboard()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()
        elif event.button.id == "btn-next":
            self._save_and_continue()
        elif event.button.id == "btn-paste":
            self._paste_from_clipboard()
        elif event.button.id == "btn-clear":
            inp = self.query_one("#api-key-input", Input)
            inp.value = ""
            inp.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "api-key-input":
            self._save_and_continue()

    def _paste_from_clipboard(self) -> None:
        clip = get_system_clipboard().strip()
        if not clip:
            self.notify("Clipboard is empty or could not be read.", severity="warning")
            return
        inp = self.query_one("#api-key-input", Input)
        inp.value = clip
        inp.focus()
        self.notify("API key pasted from clipboard.", severity="information")

    def _save_and_continue(self) -> None:
        key = self.query_one("#api-key-input", Input).value.strip()
        if not key:
            self.notify("Please enter your API key.", severity="warning")
            return
        self.app.api_key = key
        self.app.push_screen("confirm")

