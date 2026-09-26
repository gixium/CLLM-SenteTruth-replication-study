"""
tui/config.py
Central configuration: model metadata, decoding configs, dataset/split specs,
and the canonical path-building function used by the entire TUI.
"""
from __future__ import annotations
import os

# ── Repository root ─────────────────────────────────────────────────────────
# This file lives at  <repo>/tui/config.py
REPO_ROOT: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── Default output root ──────────────────────────────────────────────────────
# Results are written to replication/ inside the repository (git-ignored)
# so the pre-computed simulations/ folder is never overwritten.
DEFAULT_OUTPUT_ROOT: str = os.path.normpath(os.path.join(REPO_ROOT, "replication"))


# ── Model definitions ────────────────────────────────────────────────────────
# "configs" lists which decoding config keys (C1–C5) are valid for each model.
MODELS: dict[str, dict] = {
    "gpt4omini": {
        "label":     "GPT-4o-mini",
        "excel_tag": "GPT4o-mini",
        "provider":  "openai",
        "api_name":  "gpt-4o-mini",
        "configs":   ["C1", "C2", "C3", "C4", "C5"],
    },
    "gemini2.5flashlite": {
        "label":     "Gemini-2.5-flash-lite",
        "excel_tag": "GEMINI2.5-flash-lite",
        "provider":  "gemini",
        "api_name":  "gemini-2.5-flash-lite-preview-06-17",
        "configs":   ["C1", "C2", "C3", "C4", "C5"],
    },
    "deepseek-chat": {
        "label":     "DeepSeek-v4-flash (chat mode)",
        "excel_tag": "deepseek-chat",
        "provider":  "deepseek",
        "api_name":  "deepseek-chat",
        "configs":   ["C1", "C2", "C3", "C4"],
    },
    "deepseek-reasoner": {
        "label":     "DeepSeek-v4-flash (reasoner mode)",
        "excel_tag": "deepseek-reasoner",
        "provider":  "deepseek",
        "api_name":  "deepseek-reasoner",
        "configs":   ["C1", "C2", "C3", "C4"],
    },
}

# ── Decoding configurations ──────────────────────────────────────────────────
# "prefix" is the directory-name prefix used in simulations/ folders.
DECODING_CONFIGS: dict[str, dict] = {
    "C1": {
        "label":  "C1: temp=0.0 (deterministic)",
        "prefix": "temp-0",
        "temp":   0.0,
        "seed":   None,
    },
    "C2": {
        "label":  "C2: temp=0.5",
        "prefix": "temp-0.5",
        "temp":   0.5,
        "seed":   None,
    },
    "C3": {
        "label":  "C3: temp=1.0 (default)",
        "prefix": "temp-default",
        "temp":   1.0,
        "seed":   None,
    },
    "C4": {
        "label":  "C4: temp=1.0 + seed=4321",
        "prefix": "seed-4321",
        "temp":   1.0,
        "seed":   4321,
    },
    "C5": {
        "label":  "C5: temp=1.5 [GPT-4o-mini & Gemini]",
        "prefix": "temp-1.5",
        "temp":   1.5,
        "seed":   None,
    },
}

# ── Dataset definitions ──────────────────────────────────────────────────────
DATASETS: dict[str, dict] = {
    "MIX": {
        "label":        "MIX: 100 questions (30 shuffles)",
        "number":       "100",
        "num_shuffles": 30,
        "src_file":     "q_100_MIX.json",   # in dataset-questions_translated/
        "dst_file":     "q_100.json",        # expected by pipeline scripts
    },
    "PRO": {
        "label":        "PRO: 60 questions (20 shuffles)",
        "number":       "60",
        "num_shuffles": 20,
        "src_file":     "q_60_PRO.json",
        "dst_file":     "q_60.json",
    },
}

# ── Node-split definitions ───────────────────────────────────────────────────
SPLITS: dict[str, dict] = {
    "60-40": {
        "label":      "60-40: 6 honest / 4 malicious",
        "good_nodes": 6,
    },
    "70-30": {
        "label":      "70-30: 7 honest / 3 malicious",
        "good_nodes": 7,
    },
}


# ── Path builder ─────────────────────────────────────────────────────────────

def build_sim_path(output_root: str, split: str, decoding: str,
                   dataset: str, model: str) -> str:
    """
    Construct the simulation directory path that mirrors the repository convention:

        <output_root>/simulations <split>/<prefix>_run_<dataset>_<model>/

    Example:
        ../replication/simulations 60-40/temp-0_run_MIX_gpt4omini/
    """
    prefix = DECODING_CONFIGS.get(decoding, {}).get("prefix", "temp-default")
    split_dir = f"simulations {split}" if split else "simulations"
    return os.path.join(
        output_root,
        split_dir,
        f"{prefix}_run_{dataset}_{model}",
    )


def dataset_src_path(dataset: str) -> str:
    """Full path to the original question file in dataset-questions_translated/."""
    return os.path.join(
        REPO_ROOT,
        "dataset-questions_translated",
        DATASETS[dataset]["src_file"],
    )
