"""
tui/screens/dataset_select.py
Dataset + node-split + decoding-config selection.
Also handles model selection for Verify mode (where model_select is skipped).
"""
from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import (
    Button, Footer, Header, RadioButton, RadioSet, Static,
)
from textual.containers import Center, Horizontal, Vertical
from textual.reactive import reactive

from tui.config import DATASETS, SPLITS, DECODING_CONFIGS, MODELS


def _clean_id(k: str) -> str:
    return k.replace(".", "_")


class DatasetSelectScreen(Screen):
    """
    Three-panel selection: dataset / node split / decoding config.
    In Verify mode a fourth panel for model selection is prepended.
    """

    CSS = """
    DatasetSelectScreen {
        align: center middle;
        overflow-y: auto;
        background: #000000;
        color: #ffffff;
    }
    #outer-box {
        width: 96;
        height: auto;
        padding: 1 2;
        border: solid #ffffff;
        background: #000000;
    }
    #columns {
        height: auto;
    }
    .column {
        width: 1fr;
        height: auto;
        margin: 0 1;
    }
    .panel-title {
        color: #ffffff;
        text-style: bold;
        margin-bottom: 0;
    }
    .panel {
        height: auto;
        padding: 0 1;
        margin-bottom: 1;
        border: solid #555555;
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
    RadioSet {
        height: auto;
        background: #000000;
    }
    """

    def compose(self) -> ComposeResult:
        mode = getattr(self.app, "mode", "verify")
        step_label = "Step 2 of 4" if mode == "full" else "Step 1 of 2"

        yield Header(show_clock=False)
        with Center():
            with Vertical(id="outer-box"):
                yield Static(
                    f"[bold]{step_label}: Select Configuration[/]\n"
                )
                with Horizontal(id="columns"):
                    # ── Left Column: Model + Dataset ─────────────────────────
                    with Vertical(classes="column"):
                        if mode == "verify":
                            with Vertical(classes="panel"):
                                yield Static("Model", classes="panel-title")
                                with RadioSet(id="model-set"):
                                    for key, meta in MODELS.items():
                                        yield RadioButton(
                                            meta["label"], id=f"m-{_clean_id(key)}", name=key
                                        )

                        with Vertical(classes="panel"):
                            yield Static("Dataset", classes="panel-title")
                            with RadioSet(id="dataset-set"):
                                for key, meta in DATASETS.items():
                                    yield RadioButton(meta["label"], id=f"d-{_clean_id(key)}", name=key)

                    # ── Right Column: Node Split + Decoding Config ───────────
                    with Vertical(classes="column"):
                        with Vertical(classes="panel"):
                            yield Static("Node Split", classes="panel-title")
                            with RadioSet(id="split-set"):
                                for key, meta in SPLITS.items():
                                    yield RadioButton(meta["label"], id=f"s-{_clean_id(key)}", name=key)

                        with Vertical(classes="panel"):
                            yield Static("Decoding Config", classes="panel-title")
                            with RadioSet(id="config-set"):
                                for key, meta in DECODING_CONFIGS.items():
                                    yield RadioButton(meta["label"], id=f"c-{_clean_id(key)}", name=key)

                with Horizontal(id="btn-row"):
                    yield Button("Back", id="btn-back")
                    yield Button("Next", id="btn-next")
        yield Footer()



    def on_mount(self) -> None:
        """Restore previously selected values or set defaults."""
        app = self.app
        mode = getattr(app, "mode", "verify")

        dataset = getattr(app, "selected_dataset", "") or "MIX"
        split = getattr(app, "selected_split", "") or "60-40"
        decoding = getattr(app, "selected_decoding", "") or "C1"

        self._try_select("dataset-set", f"d-{_clean_id(dataset)}")
        self._try_select("split-set",   f"s-{_clean_id(split)}")
        self._try_select("config-set",  f"c-{_clean_id(decoding)}")
        if mode == "verify":
            model = getattr(app, "selected_model", "") or "gpt4omini"
            self._try_select("model-set", f"m-{_clean_id(model)}")

    def _try_select(self, set_id: str, btn_id: str) -> None:
        try:
            if btn_id.endswith("-"):
                return
            self.query_one(f"#{btn_id}", RadioButton).value = True
        except Exception:
            pass

    # ── Dynamic C5 visibility ─────────────────────────────────────────────────

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """Hide C5 if DeepSeek is selected (C5 not available for DeepSeek)."""
        if event.radio_set.id == "model-set":
            selected = event.pressed.name or event.pressed.id.removeprefix("m-")
            c5_btn = self.query_one("#c-C5", RadioButton)
            if selected.startswith("deepseek"):
                c5_btn.display = False
                # If C5 was selected, reset to C1
                if c5_btn.value:
                    c5_btn.value = False
                    try:
                        self.query_one("#c-C1", RadioButton).value = True
                    except Exception:
                        pass
            else:
                c5_btn.display = True

    # ── Navigation ────────────────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-back":
            self.app.pop_screen()  # type: ignore[attr-defined]
        elif event.button.id == "btn-next":
            self._save_and_continue()

    def _save_and_continue(self) -> None:
        app = self.app
        mode = getattr(app, "mode", "verify")
        errors: list[str] = []

        # ── Model (Verify mode) ───────────────────────────────────────────────
        if mode == "verify":
            m = self._get_selected("model-set", "m-")
            if not m:
                errors.append("model")
            else:
                app.selected_model = m  # type: ignore[attr-defined]

        # ── Dataset ───────────────────────────────────────────────────────────
        d = self._get_selected("dataset-set", "d-")
        if not d:
            errors.append("dataset")
        else:
            app.selected_dataset = d  # type: ignore[attr-defined]

        # ── Split ─────────────────────────────────────────────────────────────
        s = self._get_selected("split-set", "s-")
        if not s:
            errors.append("node split")
        else:
            app.selected_split = s  # type: ignore[attr-defined]

        # ── Decoding ──────────────────────────────────────────────────────────
        c = self._get_selected("config-set", "c-")
        if not c:
            errors.append("decoding config")
        else:
            app.selected_decoding = c  # type: ignore[attr-defined]

        if errors:
            self.notify(
                f"Please select: {', '.join(errors)}.", severity="warning"
            )
            return

        if mode == "full":
            app.push_screen("api_key")   # type: ignore[attr-defined]
        else:
            app.push_screen("confirm")   # type: ignore[attr-defined]

    def _get_selected(self, set_id: str, prefix: str) -> str:
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
