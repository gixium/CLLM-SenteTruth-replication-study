#!/bin/bash
# =============================================================================
# run_experiment.sh — GPT-4o mini SenteTruth Experiment Automation
# =============================================================================
# Usage:  chmod +x run_experiment.sh && ./run_experiment.sh
#
# This script guides you through every phase of the experiment.
# It checks prerequisites, lets you pick what to run, confirms before
# spending money, and handles cleanup of stale files.
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
NC='\033[0m' # No Color

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
    read -p "  Continue? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipped."
        return 1
    fi
    return 0
}

# ─── Phase 0: Prerequisites ─────────────────────────────────────────────────

check_prerequisites() {
    print_header "PHASE 0: Checking Prerequisites"
    
    local all_ok=true

    # Python
    print_step "Python 3..."
    if command -v python3 &>/dev/null; then
        local pyver
        pyver=$(python3 --version 2>&1)
        print_ok "$pyver"
    else
        print_err "python3 not found. Install Python 3.9+ first."
        all_ok=false
    fi

    # Required packages
    print_step "Python packages..."
    local pkgs=("openai" "torch" "transformers" "sklearn" "numpy" "openpyxl")
    for pkg in "${pkgs[@]}"; do
        if python3 -c "import $pkg" 2>/dev/null; then
            print_ok "$pkg"
        else
            print_err "$pkg not installed"
            all_ok=false
        fi
    done

    # Scripts
    print_step "Experiment scripts..."
    local scripts=("gpt4o_mini_API.py" "shuffle_gpt4omini.py" "calc_cred_gpt4omini.py" "calc_cred_shuffle_gpt4omini.py")
    for s in "${scripts[@]}"; do
        if [[ -f "$s" ]]; then
            print_ok "$s"
        else
            print_err "$s missing"
            all_ok=false
        fi
    done

    # Question files
    print_step "Question files..."
    local qfiles=(
        "simulations 60-40/run_MIX_gpt4omini/q_100.json"
        "simulations 60-40/run_PRO_gpt4omini/q_60.json"
        "simulations 70-30/run_MIX_gpt4omini/q_100.json"
        "simulations 70-30/run_PRO_gpt4omini/q_60.json"
    )
    for qf in "${qfiles[@]}"; do
        if [[ -f "$qf" ]]; then
            local count
            count=$(python3 -c "import json; print(len(json.load(open('$qf'))))" 2>/dev/null)
            print_ok "$qf ($count questions)"
        else
            print_err "$qf missing"
            all_ok=false
        fi
    done

    # API key check
    print_step "API key in gpt4o_mini_API.py..."
    if grep -q "sk-APIKEY" gpt4o_mini_API.py; then
        print_warn "API key is still the placeholder 'sk-APIKEY'. Edit gpt4o_mini_API.py line 8 first!"
        all_ok=false
    else
        print_ok "API key is set (non-placeholder)"
    fi

    # Directories
    print_step "Output directories..."
    local dirs=(
        "simulations 60-40/run_MIX_gpt4omini/shuffle"
        "simulations 60-40/run_PRO_gpt4omini/shuffle"
        "simulations 70-30/run_MIX_gpt4omini/shuffle"
        "simulations 70-30/run_PRO_gpt4omini/shuffle"
    )
    for d in "${dirs[@]}"; do
        if [[ -d "$d" ]]; then
            print_ok "$d"
        else
            mkdir -p "$d"
            print_ok "$d (created)"
        fi
    done

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
    echo "  2) PRO  60-40  (60 Qs, 6 honest / 4 malicious, 20 shuffles)"
    echo "  3) MIX  70-30  (100 Qs, 7 honest / 3 malicious, 30 shuffles)"
    echo "  4) PRO  70-30  (60 Qs, 7 honest / 3 malicious, 20 shuffles)"
    echo "  5) ALL  (runs 1-4 sequentially)"
    echo ""
    read -p "  Enter choice [1-5]: " choice

    case $choice in
        1) CONFIGS=("MIX_60-40") ;;
        2) CONFIGS=("PRO_60-40") ;;
        3) CONFIGS=("MIX_70-30") ;;
        4) CONFIGS=("PRO_70-30") ;;
        5) CONFIGS=("MIX_60-40" "PRO_60-40" "MIX_70-30" "PRO_70-30") ;;
        *) echo "Invalid choice."; exit 1 ;;
    esac
}

# ─── Phase selector ─────────────────────────────────────────────────────────

select_phase() {
    print_header "SELECT PHASE"
    echo "  Which phase do you want to run?"
    echo ""
    echo "  1) Answer Generation      (API calls — costs money!)"
    echo "  2) Shuffle Generation      (local — instant)"
    echo "  3) Credibility Calculation (local — ~30-60 min total)"
    echo "  4) Excel Report Generation (local — instant)"
    echo "  5) ALL phases sequentially  (1 → 2 → 3 → 4)"
    echo ""
    read -p "  Enter choice [1-5]: " phase_choice
    PHASE=$phase_choice
}

# ─── Config to parameters ───────────────────────────────────────────────────

parse_config() {
    local cfg=$1
    # Parse "DATASET_CONFIG" format
    DATASET="${cfg%%_*}"       # MIX or PRO
    CONFIG="${cfg#*_}"         # 60-40 or 70-30

    if [[ "$DATASET" == "MIX" ]]; then
        NUMBER="100"
        NUM_SHUFFLES=30
    else
        NUMBER="60"
        NUM_SHUFFLES=20
    fi

    if [[ "$CONFIG" == "60-40" ]]; then
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

    local api_calls=$(( (GOOD_NODES + 2 + 1) * (NUMBER == "100" ? 100 : 60) ))
    local est_cost
    est_cost=$(python3 -c "print(f'\${$api_calls * 0.001:.2f}')")

    echo ""
    echo -e "${BOLD}  Dataset: $DATASET | Config: $CONFIG | Good nodes: $GOOD_NODES${NC}"
    echo -e "  API calls: ~$api_calls | Est. cost: ~$est_cost | Est. time: ~15-30 min"
    echo ""

    if ! confirm "This will make ~$api_calls OpenAI API calls and cost ~$est_cost. Proceed?"; then
        return 0
    fi

    # Update configuration in the script
    python3 -c "
import re

with open('gpt4o_mini_API.py', 'r') as f:
    content = f.read()

content = re.sub(r'^number = \".*\"', 'number = \"$NUMBER\"', content, flags=re.MULTILINE)
content = re.sub(r'^dataset = \".*\"', 'dataset = \"$DATASET\"', content, flags=re.MULTILINE)
content = re.sub(r'^config = \".*\"', 'config = \"$CONFIG\"', content, flags=re.MULTILINE)
content = re.sub(r'^number_of_good_nodes = \d+', 'number_of_good_nodes = $GOOD_NODES', content, flags=re.MULTILINE)

with open('gpt4o_mini_API.py', 'w') as f:
    f.write(content)

print('  Configuration updated in gpt4o_mini_API.py')
"

    print_step "Running answer generation for $DATASET $CONFIG..."
    python3 gpt4o_mini_API.py

    # Verify output
    local out_file="simulations $CONFIG/run_${DATASET}_gpt4omini/q_${NUMBER}_answers.json"
    if [[ -f "$out_file" ]]; then
        local count
        count=$(python3 -c "import json; d=json.load(open('$out_file')); print(f'{len(d)} questions, {len(d[0][\"answers\"])} answers each')")
        print_ok "Output: $out_file ($count)"
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
    if [[ ! -f "$answers_file" ]]; then
        print_err "Answers file not found: $answers_file"
        print_err "Run Phase 1 (Answer Generation) for $DATASET $CONFIG first."
        return 1
    fi

    print_step "Generating $NUM_SHUFFLES shuffles for $DATASET $CONFIG..."

    # Update configuration in shuffle script
    python3 -c "
import re

with open('shuffle_gpt4omini.py', 'r') as f:
    content = f.read()

content = re.sub(r'^number = \".*\"', 'number = \"$NUMBER\"', content, flags=re.MULTILINE)
content = re.sub(r'^dataset = \".*\"', 'dataset = \"$DATASET\"', content, flags=re.MULTILINE)
content = re.sub(r'^config = \".*\"', 'config = \"$CONFIG\"', content, flags=re.MULTILINE)
content = re.sub(r'^num_shuffles = \d+', 'num_shuffles = $NUM_SHUFFLES', content, flags=re.MULTILINE)

with open('shuffle_gpt4omini.py', 'w') as f:
    f.write(content)
"

    python3 shuffle_gpt4omini.py

    # Verify
    local shuffle_dir="simulations $CONFIG/run_${DATASET}_gpt4omini/shuffle"
    local count
    count=$(ls "$shuffle_dir"/q_*_answers_shuffle_*.json 2>/dev/null | wc -l | tr -d ' ')
    print_ok "$count shuffled files in $shuffle_dir"
}

# ─── Phase 3: Credibility Calculation ───────────────────────────────────────

run_credibility() {
    local cfg=$1
    parse_config "$cfg"

    # --- Single run ---
    local answers_file="simulations $CONFIG/run_${DATASET}_gpt4omini/q_${NUMBER}_answers.json"
    if [[ ! -f "$answers_file" ]]; then
        print_err "Answers file not found: $answers_file. Run Phase 1 first."
        return 1
    fi

    local weight_file="simulations $CONFIG/run_${DATASET}_gpt4omini/node_weights_log_run_${NUMBER}.txt"

    # Clean stale output (append mode gotcha)
    if [[ -f "$weight_file" ]]; then
        print_warn "Removing stale weight log: $weight_file"
        rm "$weight_file"
    fi

    print_step "Running single credibility calculation for $DATASET $CONFIG..."

    # Update configuration
    python3 -c "
import re

with open('calc_cred_gpt4omini.py', 'r') as f:
    content = f.read()

content = re.sub(r'^    number = \".*\"', '    number = \"$NUMBER\"', content, flags=re.MULTILINE)
content = re.sub(r'^    dataset = \".*\"', '    dataset = \"$DATASET\"', content, flags=re.MULTILINE)
content = re.sub(r'^    config = \".*\"', '    config = \"$CONFIG\"', content, flags=re.MULTILINE)

with open('calc_cred_gpt4omini.py', 'w') as f:
    f.write(content)
"

    python3 calc_cred_gpt4omini.py

    local lines
    lines=$(wc -l < "$weight_file" | tr -d ' ')
    print_ok "Single run complete: $weight_file ($lines steps)"

    # --- Shuffled runs ---
    local shuffle_dir="simulations $CONFIG/run_${DATASET}_gpt4omini/shuffle"
    local shuffle_count
    shuffle_count=$(ls "$shuffle_dir"/q_*_answers_shuffle_*.json 2>/dev/null | wc -l | tr -d ' ')
    if [[ "$shuffle_count" -eq 0 ]]; then
        print_err "No shuffled files found. Run Phase 2 first."
        return 1
    fi

    # Clean stale shuffle weight logs
    local stale
    stale=$(ls "$shuffle_dir"/node_weights_log_*.txt 2>/dev/null | wc -l | tr -d ' ')
    if [[ "$stale" -gt 0 ]]; then
        print_warn "Removing $stale stale shuffle weight logs..."
        rm "$shuffle_dir"/node_weights_log_*.txt
    fi

    print_step "Running credibility on $shuffle_count shuffled datasets for $DATASET $CONFIG..."
    echo -e "  ${YELLOW}(This can take 10-20 minutes per config)${NC}"

    # Update configuration
    python3 -c "
import re

with open('calc_cred_shuffle_gpt4omini.py', 'r') as f:
    content = f.read()

content = re.sub(r'^    number = \".*\"', '    number = \"$NUMBER\"', content, flags=re.MULTILINE)
content = re.sub(r'^    dataset = \".*\"', '    dataset = \"$DATASET\"', content, flags=re.MULTILINE)
content = re.sub(r'^    config = \".*\"', '    config = \"$CONFIG\"', content, flags=re.MULTILINE)
content = re.sub(r'^    num_shuffles = \d+', '    num_shuffles = $NUM_SHUFFLES', content, flags=re.MULTILINE)

with open('calc_cred_shuffle_gpt4omini.py', 'w') as f:
    f.write(content)
"

    python3 calc_cred_shuffle_gpt4omini.py

    local log_count
    log_count=$(ls "$shuffle_dir"/node_weights_log_*.txt 2>/dev/null | wc -l | tr -d ' ')
    print_ok "Shuffle credibility complete: $log_count weight logs in $shuffle_dir"
}

# ─── Phase 4: Excel Report ──────────────────────────────────────────────────

run_excel_report() {
    print_step "Generating Excel report..."

    if [[ ! -f "generate_excel_gpt4omini.py" ]]; then
        print_err "generate_excel_gpt4omini.py not found"
        return 1
    fi

    python3 generate_excel_gpt4omini.py

    if [[ -f "Research project GPT4o-mini.xlsx" ]]; then
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

    check_prerequisites || exit 1
    select_configs
    select_phase

    for cfg in "${CONFIGS[@]}"; do
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
                # Excel is generated once for all configs, not per-config
                ;;
            5)
                run_answer_generation "$cfg"
                run_shuffle "$cfg"
                run_credibility "$cfg"
                ;;
        esac
    done

    # Excel report (runs once regardless of config selection)
    if [[ "$PHASE" == "4" || "$PHASE" == "5" ]]; then
        run_excel_report
    fi

    print_header "🎉 DONE"
    echo "  All selected phases completed successfully."
    echo ""
}

main "$@"
