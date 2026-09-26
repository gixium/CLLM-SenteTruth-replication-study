"""
tui/screens/run.py
Live pipeline execution screen.

Runs the pipeline in an async Textual worker and streams each subprocess line
to a RichLog widget, with a step-by-step progress display.
"""
from __future__ import annotations

import asyncio

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, ProgressBar, RichLog, Static
from textual.containers import Horizontal, Vertical

from tui.config import (
    DEFAULT_OUTPUT_ROOT,
    MODELS,
    DATASETS,
    SPLITS,
    DECODING_CONFIGS,
)
from tui.runner.pipeline import (
    PipelineConfig, run_pipeline, STEP_LABELS, cancel_current_pipeline,
)


# Total number of pipeline steps (Step 1 only runs in full mode, handled below)
_TOTAL_STEPS_FULL   = 5
_TOTAL_STEPS_VERIFY = 4   # Steps 2–5


class RunScreen(Screen):
    """
    Displays live log output and step progress while the pipeline runs.
    """

    CSS = """
    RunScreen {
        layout: vertical;
        background: #000000;
        color: #ffffff;
    }
    #step-panel {
        height: auto;
        padding: 1 2;
        border-bottom: solid #555555;
        background: #000000;
        margin-bottom: 1;
    }
    #cfg-banner {
        margin: 1 0;
        padding: 0 1;
        border-left: solid #ffffff;
        background: #000000;
        color: #ffffff;
    }
    .step-row {
        height: 1;
        margin-bottom: 0;
    }
    .step-waiting  { color: #666666; }
    .step-running  { color: #ffffff; text-style: bold underline; }
    .step-done     { color: #ffffff; }
    .step-error    { color: #ffffff; text-style: bold; }
    #progress-bar {
        margin: 1 0 0 0;
        background: #000000;
    }
    #btn-bar {
        height: auto;
        margin-top: 1;
        align: left middle;
    }
    #btn-cancel {
        min-width: 14;
    }
    #cancel-hint {
        margin-left: 2;
        content-align: left middle;
        color: #888888;
    }
    #log {
        height: 1fr;
        border: none;
        background: #000000;
        color: #ffffff;
        padding: 0 2;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel_run", "Cancel", show=True),
        Binding("c", "cancel_run", "Cancel", show=False),
    ]

    def compose(self) -> ComposeResult:
        app   = self.app
        mode  = getattr(app, "mode", "verify")
        total = _TOTAL_STEPS_FULL if mode == "full" else _TOTAL_STEPS_VERIFY

        model    = getattr(app, "selected_model", "")
        dataset  = getattr(app, "selected_dataset", "")
        split    = getattr(app, "selected_split", "")
        decoding = getattr(app, "selected_decoding", "")

        m_label = MODELS.get(model, {}).get("label", model)
        d_label = DATASETS.get(dataset, {}).get("label", dataset)
        s_label = SPLITS.get(split, {}).get("label", split)
        c_label = DECODING_CONFIGS.get(decoding, {}).get("label", decoding)
        mode_str = "Verify Existing Results" if mode == "verify" else "Full Replication"

        # Dynamically align the '|' column separator regardless of label lengths
        col1_model_len = len(f"Model: {m_label}")
        col1_split_len = len(f"Split: {s_label}")
        pad_width = max(col1_model_len, col1_split_len)
        pad_model = " " * (pad_width - col1_model_len)
        pad_split = " " * (pad_width - col1_split_len)

        yield Header(show_clock=False)

        with Vertical(id="step-panel"):
            yield Static(f"[bold]Pipeline Execution[/]  [dim]({mode_str})[/]")
            yield Static(
                f"[bold]Model:[/] {m_label}{pad_model}  |  [bold]Dataset:[/]  {d_label}\n"
                f"[bold]Split:[/] {s_label}{pad_split}  |  [bold]Decoding:[/] {c_label}",
                id="cfg-banner",
            )
            all_labels = STEP_LABELS if mode == "full" else STEP_LABELS[1:]
            for lbl in all_labels:
                yield Static(f"  [ ]  {lbl}", classes="step-row step-waiting",
                             id=_step_id(lbl))
            yield ProgressBar(total=total, id="progress-bar", show_eta=False)

            with Horizontal(id="btn-bar"):
                yield Button("Cancel", id="btn-cancel")
                yield Static("[dim](or press Escape / c to stop)[/]", id="cancel-hint")

        yield RichLog(id="log", auto_scroll=True, markup=True, highlight=False)
        yield Footer()

    def on_mount(self) -> None:
        self._start_pipeline()

    # ── Worker ────────────────────────────────────────────────────────────────

    @work(exclusive=True)
    async def _start_pipeline(self) -> None:
        """Async worker: runs the pipeline generator and updates the UI."""
        app     = self.app
        log     = self.query_one("#log", RichLog)
        pb      = self.query_one("#progress-bar", ProgressBar)
        mode    = getattr(app, "mode", "verify")
        output_root = getattr(app, "output_root", DEFAULT_OUTPUT_ROOT)

        log.clear()
        pb.progress = 0

        cfg = PipelineConfig(
            mode        = mode,
            model       = getattr(app, "selected_model", ""),
            dataset     = getattr(app, "selected_dataset", ""),
            split       = getattr(app, "selected_split", ""),
            decoding    = getattr(app, "selected_decoding", ""),
            api_key     = getattr(app, "api_key", ""),
            output_root = output_root,
        )

        log.write("=== Pipeline starting ===")

        try:
            async for event_type, data in run_pipeline(cfg):
                if event_type == "info":
                    log.write(f"[dim]{data}[/]")

                elif event_type == "step_start":
                    sid = _step_id(data)
                    try:
                        row = self.query_one(f"#{sid}", Static)
                        row.update(f"  [>]  {data}")
                        row.set_classes("step-row step-running")
                    except Exception:
                        pass
                    log.write(f"\n>>> {data}")
                    log.write("-" * 60)

                elif event_type == "log":
                    log.write(data)

                elif event_type == "step_done":
                    sid = _step_id(data)
                    try:
                        row = self.query_one(f"#{sid}", Static)
                        row.update(f"  [*]  {data}")
                        row.set_classes("step-row step-done")
                    except Exception:
                        pass
                    pb.advance(1)
                    log.write(f"[DONE]")

                elif event_type == "error":
                    log.write(f"\n[ERROR] {data}")
                    self.query_one("#btn-cancel", Button).disabled = False
                    self.query_one("#btn-cancel", Button).label = "Back"
                    app.output_path = ""  # type: ignore[attr-defined]
                    return

                elif event_type == "done":
                    app.output_path = data  # type: ignore[attr-defined]
                    log.write("\n[SUCCESS] All steps completed successfully!")
                    app.push_screen("done")  # type: ignore[attr-defined]
                    return

            log.write("[ERROR] Pipeline ended unexpectedly.")
        except asyncio.CancelledError:
            log.write("\n[CANCELLED] Pipeline was stopped by user.")
            return

    # ── Cancel button & actions ───────────────────────────────────────────────

    def action_cancel_run(self) -> None:
        self._cancel()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self._cancel()

    def _cancel(self) -> None:
        cancel_current_pipeline()
        for worker in self.workers:
            worker.cancel()
        if self.app.screen is self:
            self.app.pop_screen()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _step_id(label: str) -> str:
    """Extract step number into a clean ID like 'step-1', 'step-2'."""
    import re
    match = re.search(r"Step\s*(\d+)", label, re.IGNORECASE)
    if match:
        return f"step-{match.group(1)}"
    clean = re.sub(r"[^a-zA-Z0-9_-]", "_", label.lower()).strip("_")
    return f"step-{clean}"

