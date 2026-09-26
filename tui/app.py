"""
tui/app.py
Main Textual Application class for the CLLM-SenteTruth TUI Launcher.

State is stored directly as app attributes and read by each screen.
"""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.theme import Theme
from textual.scrollbar import ScrollBarRender

# Replace Unicode fractional block characters with spaces so Windows terminals
# never display them as '?' or '??'
ScrollBarRender.VERTICAL_BARS = [" "] * 8
ScrollBarRender.HORIZONTAL_BARS = [" "] * 8

# Replace tall Unicode block border characters with clean solid box drawing
import textual._border as _tb
_tb.BORDER_CHARS["tall"] = _tb.BORDER_CHARS["solid"]

# Patch SelectCurrent arrows to clean ASCII 'v' and '^'
try:
    from textual.widgets._select import SelectCurrent, NonSelectableStatic
    def _patched_select_current_compose(self):
        yield NonSelectableStatic(self.placeholder, id="label")
        yield NonSelectableStatic("v", classes="arrow down-arrow")
        yield NonSelectableStatic("^", classes="arrow up-arrow")
    SelectCurrent.compose = _patched_select_current_compose
except Exception:
    pass

# Patch Input bindings to support Shift+Insert as well as Ctrl+V
from textual.widgets import Input
Input.BINDINGS = list(Input.BINDINGS) + [
    Binding("shift+insert", "paste", "Paste", show=False),
]

from tui.clipboard import get_system_clipboard, set_system_clipboard
from tui.config import DEFAULT_OUTPUT_ROOT
from tui.screens.welcome      import WelcomeScreen
from tui.screens.model_select import ModelSelectScreen
from tui.screens.dataset_select import DatasetSelectScreen
from tui.screens.api_key      import ApiKeyScreen
from tui.screens.confirm      import ConfirmScreen
from tui.screens.run          import RunScreen
from tui.screens.done         import DoneScreen
from tui.screens.analysis     import AnalysisScreen


MONO_THEME = Theme(
    name="monochrome",
    primary="#ffffff",
    secondary="#888888",
    warning="#ffffff",
    error="#ffffff",
    success="#ffffff",
    accent="#ffffff",
    foreground="#ffffff",
    background="#000000",
    surface="#111111",
    panel="#000000",
    boost="#222222",
    dark=True,
)


class TUILauncherApp(App):
    """
    CLLM-SenteTruth Replication Launcher.

    Screens are registered by name so they can be pushed/switched
    from anywhere without importing across screen modules.
    """

    TITLE = "CLLM-SenteTruth Replication Launcher - ICSOC 2026"
    SUB_TITLE = "DOI: 10.5281/zenodo.21430174"

    CSS = """
    Screen {
        background: #000000;
        color: #ffffff;
    }
    Header {
        background: #000000;
        color: #ffffff;
        border-bottom: solid #ffffff;
    }
    Footer {
        background: #000000;
        color: #888888;
        border-top: solid #444444;
    }
    Button {
        background: #000000;
        color: #ffffff;
        border: solid #ffffff;
    }
    Button:hover {
        background: #ffffff;
        color: #000000;
        text-style: bold;
    }
    Button:focus {
        background: #ffffff;
        color: #000000;
        text-style: bold;
    }
    RadioSet {
        background: #000000;
        border: none;
    }
    RadioButton {
        background: #000000;
        color: #888888;
    }
    RadioButton.-selected {
        color: #ffffff;
        text-style: bold;
    }
    Input {
        background: #000000;
        color: #ffffff;
        border: solid #ffffff;
    }
    Select {
        background: #000000;
        color: #ffffff;
        border: solid #ffffff;
    }
    * {
        scrollbar-background: #000000;
        scrollbar-background-hover: #000000;
        scrollbar-background-active: #000000;
        scrollbar-color: #555555;
        scrollbar-color-hover: #888888;
        scrollbar-color-active: #ffffff;
        scrollbar-corner-color: #000000;
    }
    ScrollBar {
        background: #000000;
        color: #555555;
    }
    ScrollBarCorner {
        background: #000000;
    }
    ProgressBar {
        background: #000000;
        color: #ffffff;
    }
    Bar {
        color: #ffffff;
        background: #222222;
    }
    Bar > .bar--bar {
        color: #ffffff;
        background: #222222;
    }
    Bar > .bar--complete {
        color: #ffffff;
        background: #222222;
    }
    Bar > .bar--indeterminate {
        color: #888888;
        background: #222222;
    }
    RichLog {
        background: #000000;
        color: #ffffff;
    }
    """


    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", show=True),
        Binding("escape", "go_back", "Back", show=False),
    ]

    SCREENS = {
        "welcome":        WelcomeScreen,
        "model_select":   ModelSelectScreen,
        "dataset_select": DatasetSelectScreen,
        "api_key":        ApiKeyScreen,
        "confirm":        ConfirmScreen,
        "run":            RunScreen,
        "done":           DoneScreen,
        "analysis":       AnalysisScreen,
    }

    # ── Global pipeline state ─────────────────────────────────────────────────
    mode:             str = "verify"     # "full" | "verify"
    selected_model:   str = ""
    selected_dataset: str = ""
    selected_split:   str = ""
    selected_decoding:str = ""
    api_key:          str = ""
    output_root:      str = DEFAULT_OUTPUT_ROOT
    output_path:      str = ""           # set by RunScreen when done

    # ── Initial screen ────────────────────────────────────────────────────────

    def on_mount(self) -> None:
        self.register_theme(MONO_THEME)
        self.theme = "monochrome"
        self.push_screen("welcome")

    # ── Global key bindings ───────────────────────────────────────────────────

    def action_go_back(self) -> None:
        if len(self.screen_stack) > 1:
            self.pop_screen()

    def action_quit(self) -> None:
        self.exit()

    # ── Clipboard Integration ─────────────────────────────────────────────────

    @property
    def clipboard(self) -> str:
        """Read from the OS system clipboard, falling back to in-app clipboard."""
        sys_clip = get_system_clipboard()
        if sys_clip:
            return sys_clip
        return getattr(self, "_clipboard", "")

    @clipboard.setter
    def clipboard(self, value: str) -> None:
        """Write to in-app clipboard and OS system clipboard."""
        self._clipboard = value
        set_system_clipboard(value)

