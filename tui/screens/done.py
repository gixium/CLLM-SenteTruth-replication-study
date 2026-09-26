"""tui/screens/done.py — Success screen shown after the pipeline completes."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static
from textual.containers import Center, Horizontal, Vertical

from tui.config import DEFAULT_OUTPUT_ROOT


_NEXT_STEPS = """\
[bold]Available actions:[/]

  * [bold]Run Analysis[/]: compute FCD, SCD, Astraea q*, or DeepThought baseline
  * [bold]New Run[/]: run a different model / dataset / config
  * [bold]Exit[/]: close the launcher

The Excel report is in: results/ inside your output directory.
"""


class DoneScreen(Screen):
    """Pipeline finished successfully — show output path and next-step options."""

    CSS = """
    DoneScreen {
        align: center middle;
        overflow-y: auto;
        background: #000000;
        color: #ffffff;
    }
    #done-box {
        width: 78;
        height: auto;
        padding: 1 3;
        border: solid #ffffff;
        background: #000000;
    }
    #path-box {
        margin: 1 0;
        padding: 1 2;
        border: solid #555555;
        background: #000000;
    }
    #next-steps {
        margin-top: 1;
    }
    #btn-row {
        margin-top: 1;
        height: auto;
        align: center middle;
    }
    Button {
        margin: 0 1;
        min-width: 16;
    }
    """

    def compose(self) -> ComposeResult:
        output_root = getattr(self.app, "output_path",
                              getattr(self.app, "output_root", DEFAULT_OUTPUT_ROOT))

        yield Header(show_clock=False)
        with Center():
            with Vertical(id="done-box"):
                yield Static("[bold]Pipeline Completed Successfully[/]\n")
                yield Static(
                    f"[bold]Output directory:[/]\n  {output_root}",
                    id="path-box",
                )
                yield Static(_NEXT_STEPS, id="next-steps")
                with Horizontal(id="btn-row"):
                    yield Button("Run Analysis", id="btn-analysis")
                    yield Button("New Run", id="btn-new")
                    yield Button("Exit", id="btn-exit")
        yield Footer()


    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-analysis":
            self.app.push_screen("analysis")  # type: ignore[attr-defined]
        elif event.button.id == "btn-new":
            # Reset state and go back to welcome
            self.app.selected_model    = ""   # type: ignore[attr-defined]
            self.app.selected_dataset  = ""   # type: ignore[attr-defined]
            self.app.selected_split    = ""   # type: ignore[attr-defined]
            self.app.selected_decoding = ""   # type: ignore[attr-defined]
            self.app.api_key           = ""   # type: ignore[attr-defined]
            self.app.switch_screen("welcome") # type: ignore[attr-defined]
        elif event.button.id == "btn-exit":
            self.app.exit()                   # type: ignore[attr-defined]
