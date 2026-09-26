"""
tui/screens/analysis.py
Analysis & Baseline Comparison screen.

Lets the user run the four post-pipeline analysis tools:
  A — FCD (Final Credibility Delta) with 95% CI
  B — SCD (Sustained Credibility Dominance)
  C — Astraea analytical baseline (q*)
  D — DeepThought simulation + report
"""
from __future__ import annotations

import glob
import os

from textual import work
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import (
    Button, Footer, Header, Input, Label,
    RadioButton, RadioSet, RichLog, Select, Static,
)
from textual.containers import Center, Horizontal, Vertical, ScrollableContainer

from tui.config import REPO_ROOT, DATASETS, SPLITS, DEFAULT_OUTPUT_ROOT
from tui.runner.pipeline import run_analysis_script


_ANALYSIS_DESCRIPTIONS = {
    "A": (
        "FCD: Final Credibility Delta (95% CI)",
        "Extracts the final delta from each shuffled run and computes\n"
        "mean +/- std and 95% confidence interval (Student's t-distribution).\n"
        "Requires: an Excel workbook produced by Step 5.",
    ),
    "B": (
        "SCD: Sustained Credibility Dominance",
        "Detects the first step at which malicious credibility exceeds honest\n"
        "credibility for >=10 consecutive steps, reporting incidence and mean onset.\n"
        "Requires: an Excel workbook produced by Step 5.",
    ),
    "C": (
        "Astraea q*: Analytical Baseline",
        "Computes the honest-reporter competence q* required for Astraea\n"
        "to match C-LLM's Honest Selection Rate (RQ3).\n"
        "No parameters required - uses pre-computed HSR values.",
    ),
    "D": (
        "DeepThought: Simulation + Report",
        "Runs the DeepThought reputation-weighted voting simulation\n"
        "and generates comparison charts and an Excel report (RQ3).\n"
        "Requires: dataset, node split, and assumed human reporter accuracy.",
    ),
}


class AnalysisScreen(Screen):
    """Analysis and baseline comparison launcher."""

    CSS = """
    AnalysisScreen {
        layout: vertical;
        background: #000000;
        color: #ffffff;
    }
    #top-panel {
        height: auto;
        padding: 1 3;
        border-bottom: solid #ffffff;
        background: #000000;
    }
    #content {
        height: 1fr;
        layout: horizontal;
    }
    #left {
        width: 52;
        padding: 1 2;
        border-right: solid #555555;
        background: #000000;
    }
    #right {
        width: 1fr;
        padding: 1 2;
        background: #000000;
    }
    #desc-box {
        margin-bottom: 1;
        padding: 1 2;
        border: solid #555555;
        background: #000000;
        height: auto;
    }
    #log {
        height: 1fr;
        margin-top: 1;
        background: #000000;
        color: #ffffff;
    }
    #btn-row {
        height: auto;
        align: left middle;
        margin-top: 1;
    }
    Button {
        margin: 0 1;
        min-width: 14;
    }
    RadioSet {
        height: auto;
        background: #000000;
    }
    Select {
        margin: 0 0 1 0;
        background: #000000;
        color: #ffffff;
        border: none;
        height: auto;
    }
    SelectCurrent {
        border: solid #555555;
        background: #000000;
        color: #ffffff;
        padding: 0 1;
        height: 3;
    }
    Select:focus > SelectCurrent, SelectCurrent:focus {
        border: solid #ffffff;
    }
    SelectOverlay {
        border: solid #555555;
        background: #000000;
        color: #ffffff;
    }
    OptionList {
        border: solid #555555;
        background: #000000;
        color: #ffffff;
    }
    OptionList > .option-list--option {
        color: #ffffff;
        background: #000000;
    }
    OptionList > .option-list--option-highlighted {
        color: #000000;
        background: #ffffff;
        text-style: bold;
    }
    OptionList > .option-list--option-hover {
        color: #000000;
        background: #ffffff;
    }
    Input {
        margin: 0 0 1 0;
        background: #000000;
        color: #ffffff;
        border: solid #ffffff;
    }
    """

    # Currently selected analysis
    _selected: str = "A"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)

        with Vertical(id="top-panel"):
            yield Static(
                "[bold]Analysis & Baseline Comparison[/]\n"
                "[dim]Select an analysis to run. Results are printed below.[/]"
            )

        with Horizontal(id="content"):
            # ── Left: analysis selector ───────────────────────────────────────
            with Vertical(id="left"):
                yield Static("[bold]Select analysis:[/]\n")
                with RadioSet(id="analysis-set"):
                    for key, (title, _) in _ANALYSIS_DESCRIPTIONS.items():
                        yield RadioButton(f"[{key}] {title}", id=f"a-{key}")

                yield Static("\n")
                with Horizontal(id="btn-row"):
                    yield Button("Back", id="btn-back")
                    yield Button("Run", id="btn-run")


            # ── Right: description + params + log ────────────────────────────
            with Vertical(id="right"):
                yield Static("", id="desc-box")
                with Vertical(id="params-ab"):
                    yield Static("[bold]Workbook:[/]")
                    yield Select([], id="xlsx-select", prompt="Select an Excel workbook…")
                    yield Static("", id="xlsx-empty-notice")
                with Vertical(id="params-c"):
                    yield Static(
                        "[dim]No parameters required. The script reads HSR values\n"
                        "directly from the pre-computed data.[/]"
                    )
                with Vertical(id="params-d"):
                    yield Static("[bold]Dataset:[/]")
                    yield RadioSet(
                        *(RadioButton(m["label"], id=f"dt-d-{k}", name=k) for k, m in DATASETS.items()),
                        id="dt-dataset",
                    )
                    yield Static("[bold]Node split:[/]")
                    yield RadioSet(
                        *(RadioButton(m["label"], id=f"dt-s-{k}", name=k) for k, m in SPLITS.items()),
                        id="dt-split",
                    )
                    yield Static("[bold]Human reporter accuracy:[/]")
                    yield Input(value="0.8", id="dt-accuracy", placeholder="e.g. 0.8")
                yield RichLog(id="log", auto_scroll=True, markup=True, highlight=True)

        yield Footer()

    def on_mount(self) -> None:
        self._refresh_xlsx_options()
        self._select_analysis("A")
        try:
            self.query_one("#a-A", RadioButton).value = True
            self.query_one("#dt-d-MIX", RadioButton).value = True
            self.query_one("#dt-s-60-40", RadioButton).value = True
        except Exception:
            pass

    def _refresh_xlsx_options(self) -> None:
        output_root = getattr(self.app, "output_root", DEFAULT_OUTPUT_ROOT)
        xlsx_files = self._find_xlsx(output_root)
        sel = self.query_one("#xlsx-select", Select)
        notice = self.query_one("#xlsx-empty-notice", Static)
        if xlsx_files:
            options = [(os.path.basename(f), f) for f in xlsx_files]
            sel.set_options(options)
            sel.display = True
            notice.update("")
            notice.display = False
        else:
            sel.display = False
            notice.update(
                "[dim]No Excel workbooks found in replication/results/ or results/.\n"
                "Run the main pipeline (Step 5) first.[/]"
            )
            notice.display = True

    # ── Analysis selection ────────────────────────────────────────────────────

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        if event.radio_set.id == "analysis-set":
            key = event.pressed.id.removeprefix("a-")
            self._select_analysis(key)

    def _select_analysis(self, key: str) -> None:
        self._selected = key
        title, desc = _ANALYSIS_DESCRIPTIONS.get(key, ("", ""))
        try:
            self.query_one("#desc-box", Static).update(
                f"[bold]{title}[/]\n\n{desc}"
            )
            self.query_one("#params-ab").display = (key in ("A", "B"))
            self.query_one("#params-c").display  = (key == "C")
            self.query_one("#params-d").display  = (key == "D")
            if key in ("A", "B"):
                self._refresh_xlsx_options()
        except Exception:
            pass

    # ── Run ───────────────────────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()  # type: ignore[attr-defined]
        elif event.button.id == "btn-run":
            self._run_selected()

    def _run_selected(self) -> None:
        key = self._selected
        log = self.query_one("#log", RichLog)
        log.clear()

        output_root = getattr(self.app, "output_root", DEFAULT_OUTPUT_ROOT)
        results_dir = os.path.join(output_root, "results")

        if key == "A":
            xlsx = self._get_xlsx()
            if not xlsx:
                self.notify("Please select a workbook.", severity="warning")
                return
            self._run_script([
                os.path.join(REPO_ROOT, "results", "compute_fcd_ci.py"), xlsx
            ])

        elif key == "B":
            xlsx = self._get_xlsx()
            if not xlsx:
                self.notify("Please select a workbook.", severity="warning")
                return
            self._run_script([
                os.path.join(REPO_ROOT, "results", "compute_scd.py"), xlsx
            ])

        elif key == "C":
            self._run_script([
                os.path.join(REPO_ROOT, "astraea-comparison", "q-star.py")
            ])

        elif key == "D":
            dataset  = self._get_radio("dt-dataset", "dt-d-")
            split    = self._get_radio("dt-split", "dt-s-")
            accuracy = self._get_input("dt-accuracy", "0.8")
            if not dataset or not split:
                self.notify(
                    "Please select dataset and split.", severity="warning"
                )
                return
            dt_dir = os.path.join(REPO_ROOT, "deepthought-comparison")
            # First run deepthought_sim.py …
            self._run_deepthought(dt_dir, dataset, split, accuracy)

    @work(exclusive=True)
    async def _run_script(self, args: list[str]) -> None:
        log = self.query_one("#log", RichLog)
        log.write("--- Running analysis ---\n")
        async for event_type, data in run_analysis_script(args):
            if event_type == "log":
                log.write(data)
            elif event_type == "step_start":
                log.write(f"> {data}")
            elif event_type == "step_done":
                log.write(f"\n[DONE] {data}")
            elif event_type == "error":
                log.write(f"\n[ERROR] {data}")
                return

    @work(exclusive=True)
    async def _run_deepthought(
        self, dt_dir: str, dataset: str, split: str, accuracy: str
    ) -> None:
        log = self.query_one("#log", RichLog)
        log.write("--- DeepThought simulation ---\n")

        sim_script = os.path.join(dt_dir, "deepthought_sim.py")
        rpt_script = os.path.join(dt_dir, "generate_results.py")

        for args in [
            [sim_script, "--dataset", dataset, "--split", split,
             "--accuracy", accuracy],
            [rpt_script, "--results-dir", "results"],
        ]:
            async for event_type, data in run_analysis_script(args, cwd=dt_dir):
                if event_type == "log":
                    log.write(data)
                elif event_type == "step_start":
                    log.write(f"\n> {data}")
                elif event_type == "step_done":
                    log.write(f"[DONE] {data}")
                elif event_type == "error":
                    log.write(f"[ERROR] {data}")
                    return


    # ── Helpers ───────────────────────────────────────────────────────────────

    def _find_xlsx(self, output_root: str) -> list[str]:
        results_dir = os.path.join(output_root, "results")
        # Also look in repo results/
        repo_results = os.path.join(REPO_ROOT, "results")
        files = (
            glob.glob(os.path.join(results_dir, "*.xlsx")) +
            glob.glob(os.path.join(repo_results, "*.xlsx"))
        )
        return [f for f in sorted(set(files)) if not os.path.basename(f).startswith("~$")]

    def _get_xlsx(self) -> str:
        try:
            sel = self.query_one("#xlsx-select", Select)
            return str(sel.value) if sel.value is not Select.BLANK else ""
        except Exception:
            return ""

    def _get_radio(self, set_id: str, prefix: str) -> str:
        try:
            rs = self.query_one(f"#{set_id}", RadioSet)
            btn = rs.pressed_button
            if btn is not None:
                return btn.name or btn.id.removeprefix(prefix)
            for child in rs.query(RadioButton):
                if child.value:
                    return child.name or child.id.removeprefix(prefix)
            return ""
        except Exception:
            return ""

    def _get_input(self, inp_id: str, default: str) -> str:
        try:
            return self.query_one(f"#{inp_id}", Input).value.strip() or default
        except Exception:
            return default
