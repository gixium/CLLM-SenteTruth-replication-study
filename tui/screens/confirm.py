"""tui/screens/confirm.py — Review selections before running the pipeline."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static
from textual.containers import Center, Horizontal, Vertical

from tui.config import (
    MODELS, DATASETS, SPLITS, DECODING_CONFIGS,
    build_sim_path, DEFAULT_OUTPUT_ROOT,
)


class ConfirmScreen(Screen):
    """Show a summary of all selections and the output path before running."""

    CSS = """
    ConfirmScreen {
        align: center middle;
        overflow-y: auto;
        background: #000000;
        color: #ffffff;
    }
    #confirm-box {
        width: 80;
        height: auto;
        padding: 1 3;
        border: solid #ffffff;
        background: #000000;
    }
    #summary {
        margin: 1 0;
    }
    #path-box {
        margin: 1 0;
        padding: 1 2;
        border: solid #555555;
        background: #000000;
    }
    #timing {
        color: #888888;
        margin-top: 1;
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
            with Vertical(id="confirm-box"):
                yield Static("[bold]Confirm Configuration[/]\n")
                yield Static(self._build_summary(), id="summary")
                yield Static(self._build_path_info(), id="path-box")
                yield Static(self._build_timing(), id="timing")
                with Horizontal(id="btn-row"):
                    yield Button("Back", id="btn-back")
                    yield Button("Run Pipeline", id="btn-run")
        yield Footer()



    # ── Summary builders ──────────────────────────────────────────────────────

    def _build_summary(self) -> str:
        app = self.app
        mode    = getattr(app, "mode", "verify")
        model   = getattr(app, "selected_model", "")
        dataset = getattr(app, "selected_dataset", "")
        split   = getattr(app, "selected_split", "")
        decoding= getattr(app, "selected_decoding", "")

        model_label   = MODELS.get(model, {}).get("label", model)
        dataset_label = DATASETS.get(dataset, {}).get("label", dataset)
        split_label   = SPLITS.get(split, {}).get("label", split)
        config_label  = DECODING_CONFIGS.get(decoding, {}).get("label", decoding)
        mode_label    = "Full Replication" if mode == "full" else "Verify Existing Results"

        lines = [
            f"  Mode            [bold]{mode_label}[/]",
            f"  Model           [bold]{model_label}[/]",
            f"  Dataset         [bold]{dataset_label}[/]",
            f"  Node split      [bold]{split_label}[/]",
            f"  Decoding config [bold]{config_label}[/]",
        ]
        if mode == "full":
            lines.append("  API key         [bold][provided][/]")
        return "\n".join(lines)

    def _build_path_info(self) -> str:
        app = self.app
        model   = getattr(app, "selected_model", "")
        dataset = getattr(app, "selected_dataset", "")
        split   = getattr(app, "selected_split", "")
        decoding= getattr(app, "selected_decoding", "")
        output_root = getattr(app, "output_root", DEFAULT_OUTPUT_ROOT)

        sim_path = build_sim_path(output_root, split, decoding, dataset, model)
        return (
            "[bold]Output will be written to:[/]\n"
            f"  {sim_path}\n\n"
            "[dim]This mirrors the repository simulations/ structure.[/]"
        )

    def _build_timing(self) -> str:
        app = self.app
        mode    = getattr(app, "mode", "verify")
        dataset = getattr(app, "selected_dataset", "")
        ds      = DATASETS.get(dataset, {})
        shuffles= ds.get("num_shuffles", 30)

        lines = ["[dim]Estimated runtime:"]
        if mode == "full":
            lines.append("  Step 1 (LLM calls): depends on provider API speed")
        lines.append("  Step 2 (Shuffle)  : <1 second")
        lines.append("  Step 3 (Credibility): ~15-30 seconds (batched BERT)")
        lines.append(f"  Step 4 (Shuffles) : <2 seconds ({shuffles} shuffles, cached similarity)")
        lines.append("  Step 5 (Analysis) : <1 minute[/]")
        return "\n".join(lines)


    # ── Navigation ────────────────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()  # type: ignore[attr-defined]
        elif event.button.id == "btn-run":
            from tui.screens.run import RunScreen
            self.app.push_screen(RunScreen())  # type: ignore[attr-defined]
