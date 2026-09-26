"""tui/screens/welcome.py — Welcome screen: paper info + mode selection."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, Static
from textual.containers import Center, Horizontal, Vertical


WELCOME_TEXT = """\
[bold]Assessing the Robustness of LLM-Based Oracles for Blockchain-Based Services[/]
[dim]ICSOC 2026 - DOI: 10.5281/zenodo.21430174[/]

This launcher guides you through replicating the paper's experiments.
All outputs are written to [bold]replication/[/] (git-ignored) to preserve repo data.

----------------------------------------------------------------------------
[bold]Choose an option:[/]

  [bold][1] Verify Existing Results[/] (Recommended for artifact review)
      Copies existing answer files and re-runs Steps 2-5 locally.
      [dim]No API keys or network access required.[/]

  [bold][2] Full Replication[/]
      Calls LLM APIs to generate new responses, then runs Steps 1-5.
      [dim]Requires API credentials.[/]
"""


class WelcomeScreen(Screen):
    """Initial screen: paper information and mode selection."""

    BINDINGS = [
        Binding("1", "select_verify", "Verify Existing", show=True),
        Binding("2", "select_full", "Full Replication", show=True),
    ]

    CSS = """
    WelcomeScreen {
        align: center middle;
        background: #000000;
        color: #ffffff;
    }
    #welcome-box {
        width: 78;
        height: auto;
        padding: 1 2;
        border: solid #ffffff;
        background: #000000;
    }
    #btn-row {
        margin-top: 1;
        height: auto;
        align: center middle;
    }
    Button {
        margin: 0 1;
        min-width: 24;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Center():
            with Vertical(id="welcome-box"):
                yield Static(WELCOME_TEXT)
                with Horizontal(id="btn-row"):
                    yield Button("Verify Existing Results", id="btn-verify")
                    yield Button("Full Replication", id="btn-full")
        yield Footer()

    def action_select_verify(self) -> None:
        self.app.mode = "verify"                  # type: ignore[attr-defined]
        self.app.push_screen("dataset_select")    # type: ignore[attr-defined]

    def action_select_full(self) -> None:
        self.app.mode = "full"                    # type: ignore[attr-defined]
        self.app.push_screen("model_select")      # type: ignore[attr-defined]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-verify":
            self.action_select_verify()
        elif event.button.id == "btn-full":
            self.action_select_full()
