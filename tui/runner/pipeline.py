"""
tui/runner/pipeline.py
Async pipeline orchestrator.

Runs Steps 1–5 as subprocesses (with environment-variable injection so the
original scripts don't need manual editing) and yields a stream of events that
the TUI's Run screen consumes to update the live log and progress bar.

Event stream format:  (event_type: str, data: str)
  "info"        — informational message (copy progress, etc.)
  "step_start"  — a pipeline step is beginning
  "log"         — one line of subprocess stdout/stderr
  "step_done"   — a pipeline step completed successfully
  "error"       — fatal error; pipeline aborted
  "done"        — all steps complete; data = output_root path
"""
from __future__ import annotations

import asyncio
import os
import shutil
import sys
from typing import AsyncGenerator, NamedTuple

from tui.config import (
    REPO_ROOT,
    MODELS,
    DECODING_CONFIGS,
    DATASETS,
    SPLITS,
    build_sim_path,
    dataset_src_path,
)

# ── Pipeline configuration ────────────────────────────────────────────────────

class PipelineConfig(NamedTuple):
    mode:        str   # "full" | "verify"
    model:       str   # model key, e.g. "gpt4omini"
    dataset:     str   # "MIX" | "PRO"
    split:       str   # "60-40" | "70-30"
    decoding:    str   # "C1" … "C5"
    api_key:     str   # empty in verify mode
    output_root: str   # e.g. ../replication


STEP_LABELS = [
    "Step 1: LLM Response Generation",
    "Step 2: Question Order Shuffling",
    "Step 3: Single-Run Credibility (BERT)",
    "Step 4: Multi-Run Credibility (shuffles)",
    "Step 5: Excel Report Generation",
]

# ── Subprocess streaming ──────────────────────────────────────────────────────

_current_proc: asyncio.subprocess.Process | None = None

def cancel_current_pipeline() -> None:
    """Terminate the actively running subprocess and its entire process tree."""
    global _current_proc
    if _current_proc is not None:
        try:
            pid = _current_proc.pid
            if sys.platform == "win32":
                import subprocess as _sp
                _sp.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                        capture_output=True, check=False)
            else:
                _current_proc.kill()
        except Exception:
            pass
        _current_proc = None


async def _stream_subprocess(
    cmd: list[str],
    env: dict[str, str],
    cwd: str,
) -> AsyncGenerator[str, None]:
    """Run *cmd* as a subprocess and yield stdout/stderr lines as they arrive."""
    global _current_proc
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=env,
        cwd=cwd,
    )
    _current_proc = proc
    assert proc.stdout is not None
    try:
        while True:
            raw = await proc.stdout.readline()
            if not raw:
                break
            line = raw.decode("utf-8", errors="replace").rstrip()
            if line:
                yield line
        await proc.wait()
        if proc.returncode not in (0, None):
            raise RuntimeError(
                f"Process exited with code {proc.returncode}"
            )
    finally:
        _current_proc = None
        if proc.returncode is None:
            try:
                if sys.platform == "win32":
                    import subprocess as _sp
                    _sp.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                            capture_output=True, check=False)
                else:
                    proc.kill()
                await proc.wait()
            except Exception:
                pass


# ── Environment variable builder ──────────────────────────────────────────────

def _build_env(cfg: PipelineConfig, sim_path: str) -> dict[str, str]:
    """
    Merge the current OS environment with CLLM_* variables so the pipeline
    scripts can read them via the TUI override blocks.
    """
    dc  = DECODING_CONFIGS[cfg.decoding]
    ds  = DATASETS[cfg.dataset]
    sp  = SPLITS[cfg.split]
    mdl = MODELS[cfg.model]

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"]       = "1"
    env["CLLM_PATH"]        = sim_path + os.sep   # trailing sep expected by scripts
    env["CLLM_NUMBER"]      = ds["number"]
    env["CLLM_DATASET"]     = cfg.dataset
    env["CLLM_CONFIG"]      = cfg.split            # scripts call the split "config"
    env["CLLM_SHUFFLES"]    = str(ds["num_shuffles"])
    env["CLLM_GOOD_NODES"]  = str(sp["good_nodes"])
    env["CLLM_TEMPERATURE"] = str(dc["temp"])
    env["CLLM_SEED"]        = str(dc["seed"]) if dc["seed"] is not None else "None"
    env["CLLM_PROVIDER"]    = mdl["provider"]
    env["CLLM_MODEL"]       = mdl["api_name"]
    env["CLLM_API_KEY"]     = cfg.api_key
    env["TRANSFORMERS_VERBOSITY"]          = "error"
    env["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
    env["HF_HUB_DISABLE_PROGRESS_BARS"]   = "1"
    env["TOKENIZERS_PARALLELISM"]          = "false"
    return env



# ── Main pipeline generator ───────────────────────────────────────────────────

async def run_pipeline(
    cfg: PipelineConfig,
) -> AsyncGenerator[tuple[str, str], None]:
    """
    Async generator that drives the full pipeline.

    Usage::

        async for event_type, data in run_pipeline(cfg):
            ...
    """
    if cfg.decoding not in DECODING_CONFIGS:
        yield "error", f"Invalid decoding configuration: '{cfg.decoding}'"
        return
    if cfg.dataset not in DATASETS:
        yield "error", f"Invalid dataset: '{cfg.dataset}'"
        return
    if cfg.split not in SPLITS:
        yield "error", f"Invalid node split: '{cfg.split}'"
        return
    if cfg.model not in MODELS:
        yield "error", f"Invalid model: '{cfg.model}'"
        return

    # ── Check required dependencies upfront ──────────────────────────────────
    missing_deps: list[str] = []
    for pkg_name, import_mod in [
        ("torch", "torch"),
        ("transformers", "transformers"),
        ("scikit-learn", "sklearn"),
        ("numpy", "numpy"),
        ("openpyxl", "openpyxl"),
        ("pandas", "pandas"),
        ("scipy", "scipy"),
    ]:
        try:
            __import__(import_mod)
        except ImportError:
            missing_deps.append(pkg_name)

    if missing_deps:
        yield "error", (
            f"Missing required packages: {', '.join(missing_deps)}.\n"
            "Please install dependencies by running: pip install -r requirements.txt"
        )
        return


    dc  = DECODING_CONFIGS[cfg.decoding]
    ds  = DATASETS[cfg.dataset]

    sim_path    = build_sim_path(cfg.output_root, cfg.split, cfg.decoding,
                                 cfg.dataset, cfg.model)
    results_dir = os.path.join(cfg.output_root, "results")

    # ── Create output directories ────────────────────────────────────────────
    os.makedirs(sim_path, exist_ok=True)
    os.makedirs(os.path.join(sim_path, "shuffle"), exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)

    # ── Verify mode: copy pre-computed data ──────────────────────────────────
    if cfg.mode == "verify":
        src = build_sim_path(REPO_ROOT, cfg.split, cfg.decoding,
                             cfg.dataset, cfg.model)
        yield "info", f"Copying pre-computed data..."
        yield "info", f"  from: {src}"
        yield "info", f"  to:   {sim_path}"
        if not os.path.isdir(src):
            yield "error", (
                f"Pre-computed data not found:\n  {src}\n"
                "Please check that the repository data is intact."
            )
            return
        shutil.copytree(src, sim_path, dirs_exist_ok=True)
        yield "info", "[DONE] Data copied successfully."

    # ── Full mode: copy dataset question file ────────────────────────────────
    if cfg.mode == "full":
        src_q = dataset_src_path(cfg.dataset)
        dst_q = os.path.join(sim_path, ds["dst_file"])
        if not os.path.exists(dst_q):
            if os.path.exists(src_q):
                shutil.copy2(src_q, dst_q)
                yield "info", f"[DONE] Dataset file copied: {ds['dst_file']}"
            else:
                yield "error", f"Dataset file not found: {src_q}"
                return

    python = sys.executable
    env    = _build_env(cfg, sim_path)

    # ── Steps 1–4 ────────────────────────────────────────────────────────────
    steps: list[tuple[str, str]] = []
    if cfg.mode == "full":
        steps.append((STEP_LABELS[0], os.path.join(REPO_ROOT, "generate_answers.py")))
    steps.append((STEP_LABELS[1], os.path.join(REPO_ROOT, "shuffle.py")))
    steps.append((STEP_LABELS[2], os.path.join(REPO_ROOT, "calc_cred.py")))
    steps.append((STEP_LABELS[3], os.path.join(REPO_ROOT, "calc_cred_shuffle.py")))

    for label, script in steps:
        yield "step_start", label
        try:
            async for line in _stream_subprocess([python, "-u", script], env, REPO_ROOT):
                yield "log", line
        except RuntimeError as exc:
            yield "error", f"{label} failed: {exc}"
            return
        yield "step_done", label

    # ── Step 5: generate_excel.py (needs extra vars) ─────────────────────────
    excel_env = env.copy()
    excel_env["CLLM_MODEL_SUFFIX"]    = cfg.model
    excel_env["CLLM_DECODING_PREFIX"] = dc["prefix"] + "_"
    excel_env["CLLM_PROJECT_DIR"]     = cfg.output_root
    model_tag = MODELS.get(cfg.model, {}).get("excel_tag", cfg.model)
    prefix = dc.get("prefix", "temp-default")
    excel_output = os.path.join(
        results_dir,
        f"{prefix}_Research-project_{model_tag}_replication.xlsx",
    )
    excel_env["CLLM_OUTPUT_FILE"] = excel_output

    yield "step_start", STEP_LABELS[4]
    try:
        async for line in _stream_subprocess(
            [python, "-u", os.path.join(REPO_ROOT, "generate_excel.py")],
            excel_env,
            REPO_ROOT,
        ):
            yield "log", line
    except RuntimeError as exc:
        yield "error", f"{STEP_LABELS[4]} failed: {exc}"
        return
    yield "step_done", STEP_LABELS[4]

    yield "done", cfg.output_root


# ── Analysis / baseline runners ───────────────────────────────────────────────

async def run_analysis_script(
    script_args: list[str],
    cwd: str | None = None,
) -> AsyncGenerator[tuple[str, str], None]:
    """
    Run an analysis or baseline script (FCD, SCD, Astraea, DeepThought).
    Yields ("log", line) tuples; raises RuntimeError on non-zero exit.
    """
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"]       = "1"
    effective_cwd = cwd or REPO_ROOT
    python = sys.executable
    cmd = [python, "-u"] + script_args

    yield "step_start", " ".join(os.path.basename(a) for a in script_args[:2])
    try:
        async for line in _stream_subprocess(cmd, env, effective_cwd):
            yield "log", line
    except RuntimeError as exc:
        yield "error", str(exc)
        return
    yield "step_done", "Analysis complete"

