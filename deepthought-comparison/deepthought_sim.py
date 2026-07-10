#!/usr/bin/env python3
"""
deepthought_sim.py — DeepThought Oracle Simulation Engine

Pure-Python reimplementation of DeepThought's reputation-weighted voting
truth-discovery algorithm for comparison against CLLM-SenteTruth.

Implements the core algorithm from:
  Di Gennaro et al., "DeepThought: a Reputation and Voting-based Blockchain
  Oracle", ICSOC 2022. (arXiv: 2209.11032)

No blockchain, smart contracts, or Web3 required.

Usage:
    python3 deepthought_sim.py --dataset MIX --split 60-40 --accuracy 0.8
    python3 deepthought_sim.py --dry-run          # quick sanity check
    python3 deepthought_sim.py --help              # all options

Author: Research Project — CLLM-SenteTruth Replication Study
"""

import argparse
import csv
import math
import os
import random
import sys
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# ---------------------------------------------------------------------------
# Optional tqdm — graceful fallback
# ---------------------------------------------------------------------------
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        return iterable

# Data Structures

@dataclass
class Voter:
    """Represents a voter in the DeepThought oracle."""
    index: int
    is_honest: bool
    reputation: int = 1          # starts at 1 (DT default)
    stake: float = 100.0         # uniform stake
    last_vote: Optional[bool] = None   # True = voted TRUE, False = voted FALSE

    def cast_vote(self, ground_truth: bool, accuracy: float, rng: random.Random) -> bool:
        """
        Cast a vote on a proposition.

        Honest voters: vote correctly with probability = accuracy.
        Adversarial voters: ALWAYS vote opposite to ground truth.
        """
        if self.is_honest:
            self.last_vote = (rng.random() < accuracy) == ground_truth
        else:
            self.last_vote = not ground_truth   # always wrong
        return self.last_vote


@dataclass
class PropositionResult:
    """Result of evaluating a single proposition."""
    index: int
    outcome: Optional[bool]     # True, False, or None (Unknown)
    true_weight: float
    false_weight: float
    corrupted: bool             # True if outcome != ground_truth


# Core Algorithm

def vote_weight(stake: float, reputation: int, alpha: float) -> float:
    """
    DeepThought Eq. 3 — Vote weight function.

    f(s, r) = [α · √s + (1 − α) · s] · √r

    Parameters
    ----------
    stake : float
        Amount staked by the voter.
    reputation : int
        Current reputation score (1–max_rep).
    alpha : float
        Balance parameter in [0, 1]. Default 0.70.
        Higher α → more diminishing returns on stake.

    Returns
    -------
    float
        The computed vote weight.
    """
    return (alpha * math.sqrt(stake) + (1 - alpha) * stake) * math.sqrt(reputation)


def simulate_proposition(
    voters: List[Voter],
    ground_truth: bool,
    accuracy: float,
    alpha: float,
    max_reputation: int,
    rng: random.Random,
) -> PropositionResult:
    """
    Simulate one proposition through the DeepThought voting process.

    Steps:
    1. Each voter casts a TRUE/FALSE vote
    2. Compute weighted sums for TRUE and FALSE
    3. Determine outcome by weighted majority
    4. Update reputations based on outcome

    Parameters
    ----------
    voters : list of Voter
        All voters participating.
    ground_truth : bool
        The true answer (always True in our setup).
    accuracy : float
        Honest voter correctness probability.
    alpha : float
        Vote weight parameter.
    max_reputation : int
        Maximum reputation cap.
    rng : random.Random
        Seeded random number generator.

    Returns
    -------
    PropositionResult
    """
    # Step 1: Cast votes
    for voter in voters:
        voter.cast_vote(ground_truth, accuracy, rng)

    # Step 2: Compute weighted sums
    true_weight = 0.0
    false_weight = 0.0
    for voter in voters:
        w = vote_weight(voter.stake, voter.reputation, alpha)
        if voter.last_vote:
            true_weight += w
        else:
            false_weight += w

    # Step 3: Determine outcome
    if true_weight > false_weight:
        outcome = True
    elif false_weight > true_weight:
        outcome = False
    else:
        outcome = None  # Unknown (tie)

    # Step 4: Update reputations
    if outcome is not None:
        for voter in voters:
            if voter.last_vote == outcome:
                voter.reputation = min(voter.reputation + 1, max_reputation)
            else:
                voter.reputation = max(voter.reputation - 1, 1)
    # If outcome is Unknown → reputation unchanged (DT spec)

    # A proposition is corrupted if outcome ≠ ground_truth
    corrupted = (outcome != ground_truth)

    return PropositionResult(
        index=0,  # set by caller
        outcome=outcome,
        true_weight=true_weight,
        false_weight=false_weight,
        corrupted=corrupted,
    )


# Experiment Runner

def run_single_experiment(
    n_propositions: int,
    n_honest: int,
    n_adversarial: int,
    accuracy: float,
    alpha: float,
    stake: float,
    max_reputation: int,
    seed: int,
) -> Tuple[List[PropositionResult], List[List[int]]]:
    """
    Run a single experiment: iterate over all propositions sequentially.

    Parameters
    ----------
    n_propositions : int
        Number of propositions to evaluate.
    n_honest : int
        Number of honest voters.
    n_adversarial : int
        Number of adversarial voters.
    accuracy : float
        Honest voter correctness probability.
    alpha : float
        Vote weight parameter.
    stake : float
        Uniform stake for all voters.
    max_reputation : int
        Maximum reputation cap.
    seed : int
        Random seed for reproducibility.

    Returns
    -------
    results : list of PropositionResult
        Per-proposition results in evaluation order.
    reputation_log : list of list of int
        Reputation of each voter after each proposition.
        Shape: (n_propositions, n_voters)
    """
    rng = random.Random(seed)
    n_voters = n_honest + n_adversarial

    # Initialize voters: honest first, then adversarial
    voters = []
    for i in range(n_honest):
        voters.append(Voter(index=i, is_honest=True, reputation=1, stake=stake))
    for i in range(n_adversarial):
        voters.append(Voter(index=n_honest + i, is_honest=False, reputation=1, stake=stake))

    # Shuffle proposition order (analogous to CLLM's question shuffles)
    prop_order = list(range(n_propositions))
    rng.shuffle(prop_order)

    results = []
    reputation_log = []

    for step, prop_idx in enumerate(prop_order):
        result = simulate_proposition(
            voters=voters,
            ground_truth=True,  # all propositions have ground truth = TRUE
            accuracy=accuracy,
            alpha=alpha,
            max_reputation=max_reputation,
            rng=rng,
        )
        result.index = prop_idx

        results.append(result)
        reputation_log.append([v.reputation for v in voters])

    return results, reputation_log


def run_all_experiments(args) -> dict:
    """
    Run all repetitions for a given configuration.

    Returns a summary dict with statistics.
    """
    # Parse split
    if args.split == "60-40":
        n_honest, n_adversarial = 6, 4
    elif args.split == "70-30":
        n_honest, n_adversarial = 7, 3
    else:
        parts = args.split.split("-")
        honest_pct = int(parts[0])
        n_honest = round(args.voters * honest_pct / 100)
        n_adversarial = args.voters - n_honest

    # Parse dataset → n_propositions
    if args.dry_run:
        n_propositions = 5
        n_reps = 1
    else:
        n_propositions = {"MIX": 100, "PRO": 60}.get(args.dataset.upper(), 100)
        n_reps = args.repetitions

    n_voters = n_honest + n_adversarial
    adv_control = n_adversarial / n_voters

    # Create output dirs
    raw_dir = os.path.join(args.output_dir, "raw")
    os.makedirs(raw_dir, exist_ok=True)

    # CSV output file (combined for all runs of this config)
    csv_filename = f"dt_{args.dataset}_{args.split}_acc{args.accuracy}.csv"
    csv_path = os.path.join(raw_dir, csv_filename)

    # Header
    csv_header = [
        "run", "voters", "propositions", "accuracy", "adv_control",
        "prop_corrupted", "prop_corrupted_pct", "target_corrupted",
        "alpha", "stake", "elapsed_time",
    ]

    corruption_counts = []
    target_corrupted_list = []

    print(f"\n{'=' * 65}")
    print(f"  DeepThought Simulation")
    print(f"  Dataset: {args.dataset} | Split: {args.split} | "
          f"Accuracy: {args.accuracy}")
    print(f"  Voters: {n_voters} ({n_honest}H/{n_adversarial}A) | "
          f"Propositions: {n_propositions} | Reps: {n_reps}")
    print(f"  alpha={args.alpha} | stake={args.stake} | max_rep={args.max_rep}")
    print(f"{'=' * 65}")

    with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(csv_header)

        for run_idx in tqdm(range(n_reps), desc="  Runs", disable=args.dry_run):
            seed = args.base_seed + run_idx
            t0 = time.time()

            results, reputation_log = run_single_experiment(
                n_propositions=n_propositions,
                n_honest=n_honest,
                n_adversarial=n_adversarial,
                accuracy=args.accuracy,
                alpha=args.alpha,
                stake=args.stake,
                max_reputation=args.max_rep,
                seed=seed,
            )

            elapsed = time.time() - t0

            # Count corrupted propositions
            corrupted = sum(1 for r in results if r.corrupted)
            corrupted_pct = (corrupted / n_propositions) * 100

            # Random target proposition (use the same rng for reproducibility)
            target_rng = random.Random(seed)
            target_idx = target_rng.randint(0, n_propositions - 1)
            target_result = next(
                (r for r in results if r.index == target_idx), None
            )
            target_corrupted = 1 if (target_result and target_result.corrupted) else 0

            corruption_counts.append(corrupted)
            target_corrupted_list.append(target_corrupted)

            # Write CSV row
            writer.writerow([
                run_idx + 1, n_voters, n_propositions, args.accuracy,
                round(adv_control, 2), corrupted, round(corrupted_pct, 2),
                target_corrupted, args.alpha, args.stake, round(elapsed, 4),
            ])

            # Write reputation log
            rep_filename = (f"reputation_log_{args.dataset}_{args.split}_"
                            f"acc{args.accuracy}_run{run_idx + 1}.txt")
            rep_path = os.path.join(raw_dir, rep_filename)
            with open(rep_path, "w", encoding="utf-8") as f:
                for rep_step in reputation_log:
                    f.write(" ".join(str(r) for r in rep_step) + "\n")

            # Write outcome log
            out_filename = (f"outcome_log_{args.dataset}_{args.split}_"
                            f"acc{args.accuracy}_run{run_idx + 1}.txt")
            out_path = os.path.join(raw_dir, out_filename)
            with open(out_path, "w", encoding="utf-8") as f:
                for r in results:
                    outcome_str = (
                        "TRUE" if r.outcome is True
                        else "FALSE" if r.outcome is False
                        else "UNKNOWN"
                    )
                    f.write(f"{r.index},{outcome_str},"
                            f"{r.true_weight:.4f},{r.false_weight:.4f}\n")

    # ── Summary statistics ──
    import statistics as stats

    avg_corrupted = stats.mean(corruption_counts)
    std_corrupted = stats.stdev(corruption_counts) if len(corruption_counts) > 1 else 0.0
    min_corrupted = min(corruption_counts)
    max_corrupted = max(corruption_counts)
    system_accuracy = 1.0 - (avg_corrupted / n_propositions)
    target_pct = (sum(target_corrupted_list) / len(target_corrupted_list)) * 100

    summary = {
        "dataset": args.dataset,
        "split": args.split,
        "accuracy": args.accuracy,
        "adv_control": round(adv_control, 2),
        "n_runs": n_reps,
        "corruption_avg": round(avg_corrupted, 2),
        "corruption_std": round(std_corrupted, 2),
        "corruption_min": min_corrupted,
        "corruption_max": max_corrupted,
        "system_accuracy": round(system_accuracy * 100, 2),
        "target_corrupted_pct": round(target_pct, 2),
    }

    print(f"\n  -- Results --")
    print(f"  Corruption: avg={summary['corruption_avg']:.2f} "
          f"std={summary['corruption_std']:.2f} "
          f"min={summary['corruption_min']} max={summary['corruption_max']}")
    print(f"  System Accuracy: {summary['system_accuracy']:.2f}%")
    print(f"  Target Corrupted: {summary['target_corrupted_pct']:.1f}%")
    print(f"  CSV -> {csv_path}")
    print()

    return summary


# CLI

def parse_args():
    parser = argparse.ArgumentParser(
        description="DeepThought Oracle Simulation Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 deepthought_sim.py --dataset MIX --split 60-40 --accuracy 0.8
  python3 deepthought_sim.py --dataset PRO --split 70-30 --accuracy 0.95
  python3 deepthought_sim.py --dry-run
        """,
    )

    parser.add_argument(
        "--dataset", type=str, default="MIX",
        choices=["MIX", "PRO"],
        help="Dataset to simulate: MIX (100 propositions) or PRO (60). Default: MIX",
    )
    parser.add_argument(
        "--split", type=str, default="60-40",
        help="Honest/adversarial split. Default: 60-40 (6 honest, 4 adversarial)",
    )
    parser.add_argument(
        "--accuracy", type=float, default=0.80,
        help="Honest voter correctness probability [0, 1]. Default: 0.80",
    )
    parser.add_argument(
        "--repetitions", type=int, default=30,
        help="Number of repetitions per configuration. Default: 30",
    )
    parser.add_argument(
        "--voters", type=int, default=10,
        help="Total number of voters. Default: 10 (matching CLLM)",
    )
    parser.add_argument(
        "--alpha", type=float, default=0.70,
        help="Vote weight parameter alpha in [0,1]. Default: 0.70 (DT default)",
    )
    parser.add_argument(
        "--stake", type=float, default=100.0,
        help="Uniform stake for all voters. Default: 100.0",
    )
    parser.add_argument(
        "--max-rep", type=int, default=100,
        help="Maximum reputation cap. Default: 100",
    )
    parser.add_argument(
        "--base-seed", type=int, default=42,
        help="Base random seed for reproducibility. Default: 42",
    )
    parser.add_argument(
        "--output-dir", type=str, default="results",
        help="Output directory for results. Default: results",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Quick test: 1 repetition, 5 propositions.",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    if args.dry_run:
        print("\n  DRY RUN MODE -- 1 rep, 5 propositions\n")

    summary = run_all_experiments(args)

    if args.dry_run:
        print("  Dry run complete. Everything works!\n")

    return summary


if __name__ == "__main__":
    main()
