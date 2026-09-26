# Replication Package: Assessing the Robustness of LLM-Based Blockchain Oracles

> Companion artifact for the paper accepted at **ICSOC 2026**.
> **DOI**: [10.5281/zenodo.21430174](https://doi.org/10.5281/zenodo.21430174)

## Overview

This repository contains the complete replication package for the paper *"Assessing the Robustness of LLM-Based Oracles for Blockchain-Based Services"*, accepted at the 24th International Conference on Service-Oriented Computing (ICSOC 2026).

The study evaluates the robustness of **C-LLM**, a representative LLM-based blockchain oracle, under coordinated minority attacks where malicious nodes submit semantically consistent but factually incorrect responses. The evaluation spans four LLM families, four decoding configurations, two node splits, and two datasets, and includes a comparison with the human-based oracle baselines **Astraea** and **DeepThought**.

The repository includes:
- The full experimental pipeline (source code)
- Two benchmark datasets (MIX and PRO)
- All pre-computed raw results (LLM responses, credibility logs, analysis reports)
- Baseline comparison code (Astraea analytical model, DeepThought simulation)
- Analysis scripts for the paper's metrics (HSR, FCD, SCD, q\*)

## Repository Structure

```
.
├── README.md                          # This file
├── LICENSE                            # Usage License
├── requirements.txt                   # Python dependencies
│
├── tui_launcher.py                  # Interactive TUI launcher (ICSOC artifact replication)
├── tui/                             # TUI application screens and asynchronous runners
│
├── generate_answers.py            # Step 1: LLM response generation (honest + malicious)
├── shuffle.py                     # Step 2: Question order shuffling
├── calc_cred.py                   # Step 3: Single-run credibility computation (BERT)
├── calc_cred_shuffle.py           # Step 4: Multi-run credibility computation
├── generate_excel.py              # Step 5: Excel report generation
│
├── dataset-questions_translated/      # Benchmark datasets (English)
│   ├── q_100_MIX.json                 #   100 open-ended questions, 10 domains
│   └── q_60_PRO.json                  #   60 multiple-choice physics questions, 3 levels
│
├── simulations 60-40/                 # Raw results: 6 honest / 4 malicious nodes
│   └── <config>_run_<dataset>_<model>/
│       ├── q_*.json                   #   Questions file
│       ├── q_*_answers.json           #   LLM responses (honest + colluded malicious)
│       ├── node_weights_log_run_*.txt #   Single-run credibility evolution
│       └── shuffle/                   #   Shuffled runs (20 or 30 permutations)
│           ├── q_*_answers_shuffle_*.json
│           └── node_weights_log_run_*_shuffle_*.txt
│
├── simulations 70-30/                 # Raw results: 7 honest / 3 malicious nodes
│   └── (same structure as above)
│
├── results/                           # Aggregated analysis
│   ├── *.xlsx                         #   Excel workbooks per model × config
│   ├── dashboard.xlsx                 #   Cross-model comparison dashboard
│   ├── compute_fcd_ci.py              #   Final Credibility Delta with 95% CI
│   ├── compute_scd.py                 #   Sustained Credibility Dominance analysis
│   ├── final-deltas/                  #   FCD logs per configuration
│   └── systemic-dominance/            #   SCD logs per configuration
│
├── astraea-comparison/                # Baseline: Astraea (RQ3)
│   ├── q-star.py                      #   Analytical q* solver (Eq. 5, binomial CDF)
│   └── q-star_output.txt              #   Pre-computed output
│
├── deepthought-comparison/            # Baseline: DeepThought (RQ3)
│   ├── deepthought_sim.py             #   Simulation engine (pure-Python reimplementation)
│   ├── generate_results.py            #   Aggregation, charts, and q* analysis
│   ├── convert_questions_yesno.py     #   Dataset conversion to binary propositions
│   ├── datasets/                      #   Binary proposition datasets
│   └── results/                       #   Simulation outputs, charts, Excel reports
│
└── utility/                           # Preprocessing utilities
    ├── translator.py                  #   Chinese → English translation
    ├── merge.py, merge_PRO.py         #   Answer file merging
    ├── shuffle.py                     #   Question shuffling
    ├── reorder.py, cleaning.py        #   Data cleaning
    └── BASE/                          #   Original Chinese datasets from C-LLM
```

### Naming Convention for Simulation Directories

Each simulation directory follows the pattern: `<decoding>_run_<dataset>_<model>`

| Prefix | Decoding Configuration | Temperature | Seed |
|---|---|---|---|
| `temp-0` | C1 | 0 | default |
| `temp-0.5` | C2 | 0.5 | default |
| `temp-default` | C3 | 1.0 | default |
| `seed-4321` | C4 | 1.0 | 4321 |

Models: `gpt4omini` (GPT-4o-mini), `gemini2.5flashlite` (Gemini-2.5-flash-lite), `deepseek-chat` (DeepSeek-v4-flash, chat mode), `deepseek-reasoner` (DeepSeek-v4-flash, reasoning mode).

## Prerequisites

- **Python 3.9+**
- **LLM API keys** — required **only** for Step 1 (response generation):
  - [OpenAI](https://platform.openai.com/) for GPT-4o-mini
  - [Google GenAI](https://ai.google.dev/) for Gemini-2.5-flash-lite
  - [DeepSeek](https://platform.deepseek.com/) for DeepSeek-v4-flash
- **Disk space**: ~4 GB for BERT model download (automatic on first run of Step 3)

> **Note**: Steps 2–5 and all analysis scripts run entirely locally without API keys. The pre-computed results included in this repository allow full verification without executing Step 1.

## Installation

```bash
git clone https://github.com/gixium/CLLM-SenteTruth-replication-study.git
cd CLLM-SenteTruth-replication-study
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Quick Start: Interactive Replication Launcher (TUI)

The simplest and recommended way to replicate or verify the experiments is via the interactive Terminal User Interface (TUI):

```bash
python tui_launcher.py
```

The launcher guides the user step-by-step through configuration and execution:
- **Verify Existing Results** (*Artifact Evaluation*): Copies existing simulation answers to `replication/` (git-ignored) and runs Steps 2–5 entirely locally. No API keys or external network connections are needed.
- **Full Replication**: Prompts for model provider, dataset, node split, decoding configuration, and API key, then runs Steps 1–5 end-to-end.
- **Analysis & Baselines**: Directly launch FCD (95% CI), SCD analysis, Astraea $q^*$ analytical model, or DeepThought simulation from the post-pipeline screen.

All TUI runs write their logs, shuffled answer files, credibility weights, and final Excel reports to `replication/`, keeping the repository clean.

---

## Experimental Pipeline (Manual CLI)

Reviewers can also run each step manually via the command line. The pipeline consists of five sequential steps:

### Step 1 — LLM Response Generation (requires API keys)

Generates honest and malicious LLM responses for a given configuration.

1. Open `generate_answers.py` and configure:
   - **LLM provider** (lines 6–27): uncomment the desired provider block and set your API key in `api_key="sk-APIKEY"`.
   - **Experiment parameters** (lines 30–47): set `number`, `dataset`, `config`, `number_of_good_nodes`, `model_temperature`, and `model_seed`.

2. Run:
   ```bash
   python3 generate_answers.py
   ```

3. **Output**: `simulations <config>/run_<dataset>_<model>/q_<number>_answers.json` — a JSON array where each entry contains a question and 10 answers (first N honest, last 10−N colluded malicious).

The script includes crash-safe incremental saving and automatic resume.

### Step 2 — Question Order Shuffling

Creates randomized permutations of the question order to account for sequential credibility-update effects.

1. Configure `shuffle.py` (lines 11–14): set `number`, `dataset`, `config`, `num_shuffles` (30 for MIX, 20 for PRO).

2. Run:
   ```bash
   python3 shuffle.py
   ```

3. **Output**: `simulations <config>/run_<dataset>_<model>/shuffle/q_<number>_answers_shuffle_<i>.json`

### Step 3 — Single-Run Credibility Computation

Computes C-LLM credibility updates using BERT embeddings and cosine similarity.

1. Configure `calc_cred.py` (lines 73–75): set `number`, `dataset`, `config`.

2. Run:
   ```bash
   python3 calc_cred.py
   ```

3. **Output**: `node_weights_log_run_<number>.txt` — one line per question, 10 space-separated weight values (one per node).

**Estimated time**: ~15–30 seconds per run on CPU (batched inference). Automatically saves `similarity_cache.pkl`.

> The script defaults to CPU computation for numerical reproducibility. To use Apple Silicon GPU, set `export BERT_DEVICE=mps` before running.

### Step 4 — Multi-Run Credibility Computation

Runs Step 3 across all shuffled question orderings using cached similarity matrices.

1. Configure `calc_cred_shuffle.py` (lines 84–88): set `number`, `dataset`, `config`, `num_shuffles`.

2. Run:
   ```bash
   python3 calc_cred_shuffle.py
   ```

3. **Output**: `shuffle/node_weights_log_run_<number>_shuffle_<i>.txt`

**Estimated time**: <2 seconds (using cached similarity matrices).

### Step 5 — Excel Report Generation

Compiles weight logs into an Excel workbook with per-run system accuracy, credibility deltas, and aggregate statistics.

```bash
python3 generate_excel.py
```

**Output**: Excel workbook with single-run sheets, shuffle sheets (per-run accuracy), and a final summary sheet. Output files generated via the replication pipeline are saved as `<decoding>_Research-project_<model>_replication.xlsx` (in `replication/results/`), enabling concurrent side-by-side inspection with the reference baseline workbooks in Microsoft Excel.

## Analysis Scripts

### Final Credibility Delta with 95% Confidence Interval

Extracts FCD from each shuffled run and computes mean, standard deviation, and 95% CI using Student's t-distribution:

```bash
python3 results/compute_fcd_ci.py results/<workbook>.xlsx
```

### Sustained Credibility Dominance (SCD)

Detects the first step at which dishonest group credibility exceeds honest group credibility for ≥10 consecutive steps:

```bash
python3 results/compute_scd.py results/<workbook>.xlsx
```

## Baseline Comparison (RQ3)

### Astraea — Analytical Model

Computes the honest-reporter competence q\* required for Astraea to match C-LLM's Honest Selection Rate, using the analytical binomial model (Eq. 5 from the original Astraea paper):

```bash
python3 astraea-comparison/q-star.py
```

### DeepThought — Simulation

Pure-Python reimplementation of DeepThought's reputation-weighted voting algorithm. Runs the simulation for a given configuration:

```bash
cd deepthought-comparison
python3 deepthought_sim.py --dataset MIX --split 60-40 --accuracy 0.8
python3 deepthought_sim.py --dry-run   # quick sanity check
python3 deepthought_sim.py --help      # all options
```

To generate the full comparison report (summary CSVs, Excel, charts, q\* analysis):

```bash
python3 generate_results.py --results-dir results
```

## Verification Without API Keys

All pre-computed results are included in the repository:

1. **LLM responses**: `simulations <split>/<config>_run_<dataset>_<model>/q_*_answers.json`
2. **Credibility logs**: `node_weights_log_*.txt` files in each simulation directory
3. **Analysis reports**: Excel workbooks in `results/`
4. **Baseline results**: `astraea-comparison/q-star_output.txt` and `deepthought-comparison/results/`

To verify, a reviewer can:
- Skip Step 1 and start from Step 2 using the pre-computed answer files
- Re-run Steps 3–5 to regenerate credibility logs and Excel reports
- Compare the regenerated outputs with the included results
- Re-run the analysis scripts (`compute_fcd_ci.py`, `compute_scd.py`) on the included Excel workbooks

## Technical Details

| Parameter | Value |
|---|---|
| LLM models | GPT-4o-mini, Gemini-2.5-flash-lite, DeepSeek-v4-flash (chat), DeepSeek-v4-flash (reasoner) |
| SBERT embedding model | `bert-base-uncased` (Hugging Face Transformers), mean pooling |
| Similarity metric | Pairwise cosine similarity (`sklearn.metrics.pairwise.cosine_similarity`) |
| Oracle nodes | N = 10, initialized at credibility 0.50 each |
| Node splits | 6/4 (60-40) and 7/3 (70-30) |
| Decoding configs | C1 (temp=0), C2 (temp=0.5), C3 (temp=1.0), C4 (temp=1.0, seed=4321) |
| Datasets | MIX (100 questions, 30 runs), PRO (60 questions, 20 runs) |
| Total configurations | 64 (4 models × 4 decodings × 2 datasets × 2 splits) |

## Data Format

### Question Files (`q_*.json`)
```json
[
  {"question": "What is the speed of light?", "answer": "..."},
  ...
]
```

### Answer Files (`q_*_answers.json`)
```json
[
  {
    "question": "What is the speed of light?",
    "answers": ["honest_1", "honest_2", ..., "honest_N", "malicious", "malicious", ..., "malicious"]
  },
  ...
]
```
The first N entries are honest responses (independently generated); the remaining 10−N are identical copies of the colluded malicious response.

### Credibility Logs (`node_weights_log_*.txt`)
```
0.503214 0.498721 0.512345 0.489012 0.501234 0.497654 0.508123 0.508123 0.508123 0.508123
...
```
One line per question processed. Each line contains 10 space-separated floating-point values representing the updated credibility weight of each node after that question. Columns 1–N are honest nodes; columns N+1–10 are malicious nodes.

## Citation

If you use this artifact, please cite:

```bibtex
TBA
```

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
