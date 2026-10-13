"""
StormSense Whole-Day Split Utility

Performs leak-free dataset partitioning:
1. Groups samples by distinct calendar day.
2. Shuffles days with a deterministic random seed.
3. Allocates days across train / val / test splits.
4. Enforces the 255-minute operational temporal footprint buffer:
   drops any sample within 255 minutes of any sample in a different split.
5. Computes and prints split statistics:
   - per-split days
   - sample counts
   - lightning positive rates
   - number of test days with lightning positives
6. Fails loudly if test has < 5 days with positives.
"""

import argparse
import os
import sys
import random
from datetime import datetime
import numpy as np


def run_whole_day_split(dataset_dir: str, seed: int = 42, dry_run: bool = True):
    print("=====================================================================")
    print(" StormSense - Whole-Day Splitter (Dry Run Analysis)")
    print("=====================================================================")
    print(f" Dataset Directory: {dataset_dir}")
    print(f" Random Seed:       {seed}")
    print("=====================================================================\n")

    # Collect all npz files
    all_files = []
    for root, _, files in os.walk(dataset_dir):
        for f in files:
            if f.endswith(".npz"):
                all_files.append(os.path.join(root, f))

    # De-duplicate by base filename in case multiple directories were scanned
    file_map = {}
    for f in all_files:
        base = os.path.basename(f)
        if base not in file_map:
            file_map[base] = f

    sorted_basenames = sorted(file_map.keys())
    if not sorted_basenames:
        raise FileNotFoundError(f"No .npz files found in {dataset_dir}")

    # Parse timestamps
    samples = []
    for base in sorted_basenames:
        # Expected filename format: YYYYMMDD_HHMM.npz
        ts_str = base.split(".")[0]
        try:
            ts = datetime.strptime(ts_str, "%Y%m%d_%H%M")
            day_str = ts.strftime("%Y-%m-%d")
            samples.append({
                "filename": base,
                "filepath": file_map[base],
                "timestamp": ts,
                "day": day_str,
            })
        except ValueError:
            continue

    print(f"Total valid samples indexed: {len(samples)}")
    unique_days = sorted(list(set(s["day"] for s in samples)))
    print(f"Distinct calendar days found: {len(unique_days)} -> {unique_days}\n")

    # Seeded shuffling of days
    rng = random.Random(seed)
    shuffled_days = list(unique_days)
    rng.shuffle(shuffled_days)

    # Partition days across train/val/test
    # For small datasets, if days < 3, whole-day partitioning is degenerate
    n_days = len(shuffled_days)
    if n_days == 1:
        train_days = shuffled_days[:1]
        val_days = []
        test_days = []
    elif n_days == 2:
        train_days = [shuffled_days[0]]
        val_days = [shuffled_days[1]]
        test_days = []  # No days left for test!
    else:
        n_test = max(1, int(round(n_days * 0.15)))
        n_val = max(1, int(round(n_days * 0.15)))
        n_train = n_days - n_val - n_test
        train_days = shuffled_days[:n_train]
        val_days = shuffled_days[n_train:n_train + n_val]
        test_days = shuffled_days[n_train + n_val:]

    print(f"Whole-Day Assignment (seed={seed}):")
    print(f"  Train Days ({len(train_days)}): {train_days}")
    print(f"  Val Days   ({len(val_days)}): {val_days}")
    print(f"  Test Days  ({len(test_days)}): {test_days}\n")

    # Assign samples to candidate splits
    candidate_splits = {"train": [], "val": [], "test": []}
    for s in samples:
        if s["day"] in train_days:
            candidate_splits["train"].append(s)
        elif s["day"] in val_days:
            candidate_splits["val"].append(s)
        elif s["day"] in test_days:
            candidate_splits["test"].append(s)

    # Enforce 255-minute inter-split temporal footprint buffer
    # If sample t in split A has |t - s| < 255 min for any sample s in split B (B != A), drop sample t
    final_splits = {"train": [], "val": [], "test": []}
    dropped_counts = {"train": 0, "val": 0, "test": 0}

    for split_name, split_samples in candidate_splits.items():
        other_splits = [k for k in candidate_splits if k != split_name]
        other_timestamps = [
            s["timestamp"] for k in other_splits for s in candidate_splits[k]
        ]

        for s in split_samples:
            ts = s["timestamp"]
            violates_buffer = any(
                abs((ts - other_ts).total_seconds()) / 60.0 < 255.0
                for other_ts in other_timestamps
            )
            if violates_buffer:
                dropped_counts[split_name] += 1
            else:
                final_splits[split_name].append(s)

    print("Inter-Split 255-minute Buffer Enforcement (|t - s| < 255 min):")
    for sp in ["train", "val", "test"]:
        initial_c = len(candidate_splits[sp])
        retained_c = len(final_splits[sp])
        drop_c = dropped_counts[sp]
        print(f"  Split '{sp}': {initial_c} initial -> {drop_c} dropped -> {retained_c} retained")
    print()

    # Compute lightning positive rates and day positivity
    split_stats = {}
    test_days_with_positives = 0

    for sp in ["train", "val", "test"]:
        s_list = final_splits[sp]
        sp_days = sorted(list(set(s["day"] for s in s_list)))
        total_pixels = 0
        positive_pixels = 0
        days_with_positives = set()

        for s in s_list:
            data = np.load(s["filepath"])
            if "label_lightning" in data:
                lbl = data["label_lightning"]
                pos_mask = lbl > 0.5
            elif "lightning" in data:
                lbl = data["lightning"][0]
                pos_mask = lbl > 0
            else:
                pos_mask = np.zeros((1, 1), dtype=bool)

            pos_px = int(np.sum(pos_mask))
            positive_pixels += pos_px
            total_pixels += pos_mask.size
            if pos_px > 0:
                days_with_positives.add(s["day"])

        pos_rate = positive_pixels / max(total_pixels, 1)
        split_stats[sp] = {
            "days": sp_days,
            "samples": len(s_list),
            "positive_rate": pos_rate,
            "positive_days": len(days_with_positives),
        }
        if sp == "test":
            test_days_with_positives = len(days_with_positives)

    print("Split Summary Table:")
    print(f"{'Split':>7} | {'Days Count':>10} | {'Samples':>8} | {'Lightning Pos Rate':>18} | {'Pos Days':>8}")
    print("-" * 65)
    for sp in ["train", "val", "test"]:
        st = split_stats[sp]
        print(f"{sp:>7} | {len(st['days']):>10d} | {st['samples']:>8d} | {st['positive_rate']*100:>17.4f}% | {st['positive_days']:>8d}")
    print("=" * 65)

    print(f"\nTest days with lightning positives: {test_days_with_positives}")

    # Check requirement: Fail loudly if test has < 5 days with positives
    if test_days_with_positives < 5:
        error_msg = (
            f"\n[FATAL ERROR / AUDIT FAILURE] Whole-day split check failed: "
            f"Test split has only {test_days_with_positives} day(s) with lightning positives (< 5 REQUIRED).\n"
            f"Reason: Total dataset contains only {len(unique_days)} calendar day(s) ({unique_days}). "
            f"A true whole-day train/val/test split requires at least 20+ convective days to yield >= 5 test days."
        )
        print(error_msg, file=sys.stderr)
        return False, split_stats, unique_days

    return True, split_stats, unique_days


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="StormSense whole-day dataset split dry-run")
    parser.add_argument("--data-dir", default="backend/stormsense/dataset_full/dataset/all",
                        help="Path to dataset directory containing .npz samples")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for day shuffling")
    args = parser.parse_args()

    success, stats, days = run_whole_day_split(args.data_dir, seed=args.seed)
    if not success:
        sys.exit(1)
