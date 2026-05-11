#!/bin/bash
# =============================================================================
# run_experiment.sh — GPT-4o mini SenteTruth Experiment Automation
# =============================================================================
# Compatible with: Bash 3.2+ (macOS default), Apple Silicon M4
# Usage:  chmod +x run_experiment.sh && ./run_experiment.sh
# =============================================================================

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ─── Helpers ─────────────────────────────────────────────────────────────────

print_header() {
    echo ""
    echo -e "${BOLD}${BLUE}══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${BLUE}  $1${NC}"
    echo -e "${BOLD}${BLUE}══════════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_step() {
    echo -e "${CYAN}▶ $1${NC}"
}

print_ok() {
    echo -e "${GREEN}  ✅ $1${NC}"
}

print_warn() {
    echo -e "${YELLOW}  ⚠️  $1${NC}"
}

print_err() {
    echo -e "${RED}  ❌ $1${NC}"
}

confirm() {
    echo ""
    echo -e "${YELLOW}$1${NC}"
    
    echo -e "${GREEN}  [Going for the API calls!]${NC}"

    # read -p "  Continue? [y/N] " -n 1 -r
    # echo
    # if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    #     echo "Skipped."
    #     return 1
    # fi

    return 0
}

# ─── Phase 0A: Virtual Environment Setup ────────────────────────────────────
# Must run before check_prerequisites so that all subsequent python3 calls
# go through the venv interpreter.

activate_venv() {
    print_header "PHASE 0A: Virtual Environment"

    local venv_dir="$PROJECT_DIR/.venv"
    local activate_script="$venv_dir/bin/activate"

    # ── Case 1: already activated externally ────────────────────────────────
    if [ -n "${VIRTUAL_ENV:-}" ]; then
        print_ok "Venv already active: $VIRTUAL_ENV"
        return 0
    fi

    # ── Case 2: .venv exists → activate it ──────────────────────────────────
    if [ -f "$activate_script" ]; then
        # shellcheck source=/dev/null
        source "$activate_script"
        print_ok "Activated: $venv_dir"
        return 0
    fi

    # ── Case 3: .venv is missing → warn and offer to create ─────────────────
    print_warn ".venv not found at $venv_dir"
    echo ""
    echo "  A virtual environment is required. Would you like to create one now?"
    echo "  This will run: python3 -m venv .venv"
    echo "  Then you must install packages manually:"
    echo "    source .venv/bin/activate"
    echo "    pip install openai torch transformers scikit-learn openpyxl"
    echo ""

    if confirm "Create .venv now?"; then
        if ! command -v python3 >/dev/null 2>&1; then
            print_err "python3 not found — cannot create venv. Install Python 3.9+ first."
            exit 1
        fi
        python3 -m venv "$venv_dir"
        # shellcheck source=/dev/null
        source "$activate_script"
        print_ok "Created and activated: $venv_dir"
        print_warn "Packages are NOT yet installed. Run:"
        echo "    pip install openai torch transformers scikit-learn openpyxl"
        echo ""
        confirm "Continue anyway (packages will be checked next)?" || exit 0
    else
        print_err "Cannot continue without a virtual environment."
        echo "  Create one manually, then re-run this script:"
        echo "    python3 -m venv .venv"
        echo "    source .venv/bin/activate"
        echo "    pip install openai torch transformers scikit-learn openpyxl"
        exit 1
    fi
}

# ─── Phase 0B: Prerequisites ─────────────────────────────────────────────────

check_prerequisites() {
    print_header "PHASE 0B: Checking Prerequisites"

    local all_ok=true

    # Python — after venv activation, python3 already resolves to the venv
    print_step "Python 3 (venv)..."
    if command -v python3 >/dev/null 2>&1; then
        local pyver
        pyver=$(python3 --version 2>&1)
        local pypath
        pypath=$(command -v python3)
        print_ok "$pyver  ($pypath)"
    else
        print_err "python3 not found even inside venv."
        all_ok=false
    fi

    # Required packages — test inside the now-active venv interpreter
    print_step "Python packages..."
    # Note: the scikit-learn package is imported as 'sklearn'
    local pkgs="openai torch transformers sklearn numpy openpyxl"
    for pkg in $pkgs; do
        if python3 -c "import $pkg" 2>/dev/null; then
            print_ok "$pkg"
        else
            print_err "$pkg not installed in venv"
            print_warn "  Fix: pip install $(echo $pkg | sed 's/sklearn/scikit-learn/')"
            all_ok=false
        fi
    done

    # Experiment scripts
    print_step "Experiment scripts..."
    local scripts="gpt4o_mini_API.py shuffle_gpt4omini.py calc_cred_gpt4omini.py calc_cred_shuffle_gpt4omini.py generate_excel_gpt4omini.py"
    for s in $scripts; do
        if [ -f "$s" ]; then
            print_ok "$s"
        else
            print_err "$s missing"
            all_ok=false
        fi
    done

    # Output directories
    print_step "Output directories..."
    local dirs="simulations 60-40/run_MIX_gpt4omini/shuffle
simulations 60-40/run_PRO_gpt4omini/shuffle
simulations 70-30/run_MIX_gpt4omini/shuffle
simulations 70-30/run_PRO_gpt4omini/shuffle"
    while IFS= read -r d; do
        if [ -d "$d" ]; then
            print_ok "$d"
        else
            mkdir -p "$d"
            print_ok "$d (created)"
            
            # Copy base question files to the newly created run directory
            local parent_dir=$(dirname "$d")
            if [[ "$parent_dir" == *"MIX"* ]]; then
                cp "dataset-questions_translated/q_100_MIX.json" "$parent_dir/q_100.json"
                print_ok "Copied q_100.json to $parent_dir"
            elif [[ "$parent_dir" == *"PRO"* ]]; then
                cp "dataset-questions_translated/q_60_PRO.json" "$parent_dir/q_60.json"
                print_ok "Copied q_60.json to $parent_dir"
            fi
        fi
    done <<EOF
$dirs
EOF

    # Question files
    print_step "Question files..."
    local qfiles="simulations 60-40/run_MIX_gpt4omini/q_100.json
simulations 60-40/run_PRO_gpt4omini/q_60.json
simulations 70-30/run_MIX_gpt4omini/q_100.json
simulations 70-30/run_PRO_gpt4omini/q_60.json"
    while IFS= read -r qf; do
        if [ -f "$qf" ]; then
            local count
            count=$(python3 -c "import json; print(len(json.load(open('$qf'))))" 2>/dev/null)
            print_ok "$qf ($count questions)"
        else
            print_err "$qf missing"
            all_ok=false
        fi
    done <<EOF
$qfiles
EOF

    # API key check
    print_step "API key in gpt4o_mini_API.py..."
    if grep -q "sk-APIKEY" gpt4o_mini_API.py; then
        print_warn "API key is still the placeholder 'sk-APIKEY'. Edit gpt4o_mini_API.py line 8 first!"
        all_ok=false
    else
        print_ok "API key is set (non-placeholder)"
    fi

    echo ""
    if $all_ok; then
        echo -e "${GREEN}${BOLD}All prerequisites met! ✅${NC}"
    else
        echo -e "${RED}${BOLD}Some prerequisites failed. Fix them before continuing.${NC}"
        return 1
    fi
}

# ─── Configuration selector ─────────────────────────────────────────────────

select_configs() {
    print_header "SELECT CONFIGURATION"
    echo "  Which experiment run(s) do you want to execute?"
    echo ""
    echo "  1) MIX  60-40  (100 Qs, 6 honest / 4 malicious, 30 shuffles)"
    echo "  2) PRO  60-40  (60 Qs,  6 honest / 4 malicious, 20 shuffles)"
    echo "  3) MIX  70-30  (100 Qs, 7 honest / 3 malicious, 30 shuffles)"
    echo "  4) PRO  70-30  (60 Qs,  7 honest / 3 malicious, 20 shuffles)"
    echo "  5) ALL  (runs 1-4 sequentially)"
    echo ""
    read -p "  Enter choice [1-5]: " choice

    case $choice in
        1) CONFIGS="MIX_60-40" ;;
        2) CONFIGS="PRO_60-40" ;;
        3) CONFIGS="MIX_70-30" ;;
        4) CONFIGS="PRO_70-30" ;;
        5) CONFIGS="MIX_60-40 PRO_60-40 MIX_70-30 PRO_70-30" ;;
        *) echo "Invalid choice."; exit 1 ;;
    esac
}

# ─── Phase selector ─────────────────────────────────────────────────────────

select_phase() {
    print_header "SELECT PHASE"
    echo "  Which phase do you want to run?"
    echo ""
    echo "  1) Answer Generation      (API calls — costs money!)"
    echo "  2) Shuffle Generation     (local — instant)"
    echo "  3) Credibility Calculation (local — ~30-60 min total)"
    echo "  4) Excel Report Generation (local — instant)"
    echo "  5) ALL phases sequentially (1 → 2 → 3 → 4)"
    echo ""
    read -p "  Enter choice [1-5]: " phase_choice
    PHASE=$phase_choice
}

# ─── Config to parameters ───────────────────────────────────────────────────

parse_config() {
    local cfg=$1
    # "MIX_60-40" → DATASET=MIX, CONFIG=60-40
    DATASET="${cfg%%_*}"
    CONFIG="${cfg#*_}"

    if [ "$DATASET" = "MIX" ]; then
        NUMBER="100"
        NUM_SHUFFLES=30
    else
        NUMBER="60"
        NUM_SHUFFLES=20
    fi

    if [ "$CONFIG" = "60-40" ]; then
        GOOD_NODES=6
    else
        GOOD_NODES=7
    fi
    MALICIOUS_NODES=$((10 - GOOD_NODES))
}

# ─── Phase 1: Answer Generation ─────────────────────────────────────────────

run_answer_generation() {
    local cfg=$1
    parse_config "$cfg"

    # Bash 3.2-safe arithmetic — no ternary operators inside (( ))
    local q_count
    if [ "$NUMBER" = "100" ]; then
        q_count=100
    else
        q_count=60
    fi
    local api_calls=$(( (GOOD_NODES + 2 + 1) * q_count ))

    # Cost estimate via Python (avoids float arithmetic in shell)
    local est_cost
    est_cost=$(python3 -c "print('\${:.2f}'.format($api_calls * 0.001))")

    echo ""
    echo -e "${BOLD}  Dataset: $DATASET | Config: $CONFIG | Good nodes: $GOOD_NODES | Malicious: $MALICIOUS_NODES${NC}"
    echo -e "  API calls: ~$api_calls | Est. cost: ~$est_cost | Est. time: ~15-30 min"
    echo ""

    if ! confirm "This will make ~$api_calls OpenAI API calls and cost ~$est_cost. Proceed?"; then
        return 0
    fi

    # Patch configuration into gpt4o_mini_API.py using a here-doc to avoid
    # nested quoting issues in the inline python3 -c string
    python3 - "$NUMBER" "$DATASET" "$CONFIG" "$GOOD_NODES" <<'PYEOF'
import sys, re
number, dataset, config, good_nodes = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]

with open('gpt4o_mini_API.py', 'r') as f:
    content = f.read()

content = re.sub(r'^number = ".*"',          f'number = "{number}"',     content, flags=re.MULTILINE)
content = re.sub(r'^dataset = ".*"',          f'dataset = "{dataset}"',   content, flags=re.MULTILINE)
content = re.sub(r'^config = ".*"',           f'config = "{config}"',     content, flags=re.MULTILINE)
content = re.sub(r'^number_of_good_nodes = \d+', f'number_of_good_nodes = {good_nodes}', content, flags=re.MULTILINE)

with open('gpt4o_mini_API.py', 'w') as f:
    f.write(content)

print(f'  ✓ gpt4o_mini_API.py patched: dataset={dataset}, config={config}, good_nodes={good_nodes}')
PYEOF

    print_step "Running answer generation for $DATASET $CONFIG..."
    python3 gpt4o_mini_API.py

    # Verify output
    local out_file="simulations $CONFIG/run_${DATASET}_gpt4omini/q_${NUMBER}_answers.json"
    if [ -f "$out_file" ]; then
        local info
        info=$(python3 -c "
import json
d = json.load(open('$out_file'))
print('{} questions, {} answers each'.format(len(d), len(d[0]['answers'])))
")
        print_ok "Output: $out_file ($info)"
    else
        print_err "Expected output file not found: $out_file"
        return 1
    fi
}

# ─── Phase 2: Shuffle Generation ────────────────────────────────────────────

run_shuffle() {
    local cfg=$1
    parse_config "$cfg"

    local answers_file="simulations $CONFIG/run_${DATASET}_gpt4omini/q_${NUMBER}_answers.json"
    if [ ! -f "$answers_file" ]; then
        print_err "Answers file not found: $answers_file"
        print_err "Run Phase 1 (Answer Generation) for $DATASET $CONFIG first."
        return 1
    fi

    print_step "Generating $NUM_SHUFFLES shuffles for $DATASET $CONFIG..."

    python3 - "$NUMBER" "$DATASET" "$CONFIG" "$NUM_SHUFFLES" <<'PYEOF'
import sys, re
number, dataset, config, num_shuffles = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]

with open('shuffle_gpt4omini.py', 'r') as f:
    content = f.read()

content = re.sub(r'^number = ".*"',        f'number = "{number}"',           content, flags=re.MULTILINE)
content = re.sub(r'^dataset = ".*"',        f'dataset = "{dataset}"',         content, flags=re.MULTILINE)
content = re.sub(r'^config = ".*"',         f'config = "{config}"',           content, flags=re.MULTILINE)
content = re.sub(r'^num_shuffles = \d+',    f'num_shuffles = {num_shuffles}', content, flags=re.MULTILINE)

with open('shuffle_gpt4omini.py', 'w') as f:
    f.write(content)

print(f'  ✓ shuffle_gpt4omini.py patched: num_shuffles={num_shuffles}')
PYEOF

    python3 shuffle_gpt4omini.py

    local shuffle_dir="simulations $CONFIG/run_${DATASET}_gpt4omini/shuffle"
    local count
    count=$(find "$shuffle_dir" -maxdepth 1 -name 'q_*_answers_shuffle_*.json' 2>/dev/null | wc -l | tr -d ' ')
    print_ok "$count shuffled files in $shuffle_dir"
}

# ─── Phase 3: Credibility Calculation ───────────────────────────────────────

run_credibility() {
    local cfg=$1
    parse_config "$cfg"

    # --- Guard: answers file must exist ---
    local answers_file="simulations $CONFIG/run_${DATASET}_gpt4omini/q_${NUMBER}_answers.json"
    if [ ! -f "$answers_file" ]; then
        print_err "Answers file not found: $answers_file. Run Phase 1 first."
        return 1
    fi

    # --- Single run ---
    local weight_file="simulations $CONFIG/run_${DATASET}_gpt4omini/node_weights_log_run_${NUMBER}.txt"

    # Remove stale log — calc_cred appends, so a leftover file corrupts results
    if [ -f "$weight_file" ]; then
        print_warn "Removing stale weight log: $weight_file"
        rm "$weight_file"
    fi

    print_step "Patching and running single credibility calculation for $DATASET $CONFIG..."

    python3 - "$NUMBER" "$DATASET" "$CONFIG" <<'PYEOF'
import sys, re
number, dataset, config = sys.argv[1], sys.argv[2], sys.argv[3]

with open('calc_cred_gpt4omini.py', 'r') as f:
    content = f.read()

# These vars live inside the main() function (indented), so match leading spaces
content = re.sub(r'^( +)number = ".*"',  r'\g<1>' + f'number = "{number}"',  content, flags=re.MULTILINE)
content = re.sub(r'^( +)dataset = ".*"', r'\g<1>' + f'dataset = "{dataset}"', content, flags=re.MULTILINE)
content = re.sub(r'^( +)config = ".*"',  r'\g<1>' + f'config = "{config}"',   content, flags=re.MULTILINE)

with open('calc_cred_gpt4omini.py', 'w') as f:
    f.write(content)

print(f'  ✓ calc_cred_gpt4omini.py patched: dataset={dataset}, config={config}')
PYEOF

    python3 calc_cred_gpt4omini.py

    # Verify
    if [ ! -f "$weight_file" ]; then
        print_err "Weight log not produced: $weight_file"
        return 1
    fi
    local lines
    lines=$(wc -l < "$weight_file" | tr -d ' ')
    print_ok "Single run complete: $weight_file ($lines steps)"

    # --- Shuffled runs ---
    local shuffle_dir="simulations $CONFIG/run_${DATASET}_gpt4omini/shuffle"
    local shuffle_count
    shuffle_count=$(find "$shuffle_dir" -maxdepth 1 -name 'q_*_answers_shuffle_*.json' 2>/dev/null | wc -l | tr -d ' ')
    if [ "$shuffle_count" -eq 0 ]; then
        print_err "No shuffled files found in $shuffle_dir. Run Phase 2 first."
        return 1
    fi

    # Remove stale shuffle weight logs (same append-mode issue)
    local stale
    stale=$(find "$shuffle_dir" -maxdepth 1 -name 'node_weights_log_*.txt' 2>/dev/null | wc -l | tr -d ' ')
    if [ "$stale" -gt 0 ]; then
        print_warn "Removing $stale stale shuffle weight logs..."
        find "$shuffle_dir" -maxdepth 1 -name 'node_weights_log_*.txt' -delete
    fi

    print_step "Patching and running shuffle credibility for $DATASET $CONFIG..."
    echo -e "  ${YELLOW}(This can take 10-20 minutes — BERT runs on CPU for numerical reproducibility)${NC}"

    python3 - "$NUMBER" "$DATASET" "$CONFIG" "$NUM_SHUFFLES" <<'PYEOF'
import sys, re
number, dataset, config, num_shuffles = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]

with open('calc_cred_shuffle_gpt4omini.py', 'r') as f:
    content = f.read()

content = re.sub(r'^( +)number = ".*"',       r'\g<1>' + f'number = "{number}"',               content, flags=re.MULTILINE)
content = re.sub(r'^( +)dataset = ".*"',       r'\g<1>' + f'dataset = "{dataset}"',             content, flags=re.MULTILINE)
content = re.sub(r'^( +)config = ".*"',        r'\g<1>' + f'config = "{config}"',               content, flags=re.MULTILINE)
content = re.sub(r'^( +)num_shuffles = \d+',   r'\g<1>' + f'num_shuffles = {num_shuffles}',     content, flags=re.MULTILINE)

with open('calc_cred_shuffle_gpt4omini.py', 'w') as f:
    f.write(content)

print(f'  ✓ calc_cred_shuffle_gpt4omini.py patched: num_shuffles={num_shuffles}')
PYEOF

    python3 calc_cred_shuffle_gpt4omini.py

    local log_count
    log_count=$(find "$shuffle_dir" -maxdepth 1 -name 'node_weights_log_*.txt' 2>/dev/null | wc -l | tr -d ' ')
    print_ok "Shuffle credibility complete: $log_count weight logs in $shuffle_dir"
}

# ─── Phase 4: Excel Report ──────────────────────────────────────────────────

run_excel_report() {
    print_step "Generating Excel report..."

    if [ ! -f "generate_excel_gpt4omini.py" ]; then
        print_err "generate_excel_gpt4omini.py not found"
        return 1
    fi

    python3 generate_excel_gpt4omini.py

    if [ -f "Research project GPT4o-mini.xlsx" ]; then
        print_ok "Excel report: Research project GPT4o-mini.xlsx"
    else
        print_err "Excel report was not generated"
        return 1
    fi
}

# ─── Main ────────────────────────────────────────────────────────────────────

main() {
    print_header "GPT-4o mini SenteTruth Experiment"
    echo "  Project: $PROJECT_DIR"
    echo ""

    activate_venv
    check_prerequisites || exit 1
    select_configs
    select_phase

    for cfg in $CONFIGS; do
        parse_config "$cfg"
        print_header "Running: $DATASET $CONFIG"

        case $PHASE in
            1)
                run_answer_generation "$cfg"
                ;;
            2)
                run_shuffle "$cfg"
                ;;
            3)
                run_credibility "$cfg"
                ;;
            4)
                # Excel is run once after the loop, not per-config
                ;;
            5)
                run_answer_generation "$cfg"
                run_shuffle "$cfg"
                run_credibility "$cfg"
                ;;
            *)
                print_err "Unknown phase: $PHASE"
                exit 1
                ;;
        esac
    done

    # Excel report — generated once regardless of how many configs were selected
    if [ "$PHASE" = "4" ] || [ "$PHASE" = "5" ]; then
        run_excel_report
    fi

    print_header "DONE"
    echo "  All selected phases completed successfully."
    echo ""
}

main "$@"
