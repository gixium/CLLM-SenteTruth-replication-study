"""tui/screens/model_select.py — Model selection screen (Full mode only)."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, RadioButton, RadioSet, Static
from textual.containers import Center, Horizontal, Vertical

from tui.config import MODELS


def _clean_id(k: str) -> str:
    return k.replace(".", "_")


class ModelSelectScreen(Screen):
    """Let the user choose which LLM to test (shown in Full Replication mode)."""

    CSS = """
    ModelSelectScreen {
        align: center middle;
        overflow-y: auto;
        background: #000000;
        color: #ffffff;
    }
    #model-box {
        width: 70;
        height: auto;
        padding: 1 3;
        border: solid #ffffff;
        background: #000000;
    }
    RadioSet {
        margin: 1 0;
        background: #000000;
    }
    #btn-row {
        margin-top: 1;
        height: auto;
        align: center middle;
    }
    Button {
        margin: 0 2;
        min-width: 16;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Center():
            with Vertical(id="model-box"):
                yield Static(
                    "[bold]Step 1 of 3: Select Model[/]\n\n"
                    "Choose the LLM you want to test. Each model requires its own "
                    "API key on the next screen.\n"
                )
                with RadioSet(id="model-set"):
                    for key, meta in MODELS.items():
                        yield RadioButton(meta["label"], id=f"model-{_clean_id(key)}", name=key)
                with Horizontal(id="btn-row"):
                    yield Button("Back", id="btn-back")
                    yield Button("Next", id="btn-next")
        yield Footer()



    def on_mount(self) -> None:
        # Pre-select the currently stored model or default to gpt4omini
        current = getattr(self.app, "selected_model", "") or "gpt4omini"
        try:
            self.query_one(f"#model-{_clean_id(current)}", RadioButton).value = True
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()  # type: ignore[attr-defined]
        elif event.button.id == "btn-next":
            self._save_and_continue()

    def _save_and_continue(self) -> None:
        radio_set = self.query_one("#model-set", RadioSet)
        selected = radio_set.pressed_button
        if selected is None:
            for child in radio_set.query(RadioButton):
                if child.value:
                    selected = child
                    break
        if selected is None:
            self.notify("Please select a model.", severity="warning")
            return
        # Extract model key from button name or button id: "model-{key}"
        model_key = selected.name or selected.id.removeprefix("model-")  # type: ignore[union-attr]
        self.app.selected_model = model_key              # type: ignore[attr-defined]
        self.app.push_screen("dataset_select")           # type: ignore[attr-defined]
