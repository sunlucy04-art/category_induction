"""
Merges the per-condition trial lists (master_trial_list_<run_name>.csv,
one per condition — generate these first by running generate_trials.py
once per condition, changing SETTINGS["run_name"]/["outlines_dir"]/
["fill_dir"]/["shapes_dir"]/["painter_name_offset"] between runs) into the
single, shuffled master_trial_list.csv the live experiment actually reads.

Adds a "condition" column (from each input file's name) and renumbers
trial_id across the merged, shuffled set. Also refreshes
instructions_example.csv from the merged list's first row.
"""

from pathlib import Path
import csv
import random

ROOT = Path(__file__).resolve().parent

# If you keep the same seed, re-running this produces the same shuffled
# order again. Change it for a new random order.
RANDOM_SEED = 20260909

# (condition label, input file) pairs to merge. Add more entries here if you
# ever have more than two conditions.
CONDITION_FILES = [
    ("high_nameability", ROOT / "master_trial_list_high_nameability.csv"),
    ("low_nameability", ROOT / "master_trial_list_low_nameability.csv"),
]


def read_csv(path):
    with path.open(newline="") as file:
        return list(csv.DictReader(file))


def write_csv(path, rows):
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main():
    all_rows = []
    for condition, path in CONDITION_FILES:
        if not path.exists():
            raise FileNotFoundError(
                f"{path} not found — run generate_trials.py with SETTINGS pointed at the "
                f"'{condition}' stimuli first."
            )
        rows = read_csv(path)
        for row in rows:
            row["condition"] = condition
        all_rows.extend(rows)
        print(f"{condition}: {len(rows)} trials from {path.name}")

    rng = random.Random(RANDOM_SEED)
    rng.shuffle(all_rows)

    for index, row in enumerate(all_rows, start=1):
        row["trial_id"] = f"trial_{index:03d}"

    # "condition" first, since DictWriter's column order comes from the
    # first row's key insertion order and it was added last above.
    ordered_rows = []
    for row in all_rows:
        ordered = {"trial_id": row["trial_id"], "condition": row["condition"]}
        ordered.update({k: v for k, v in row.items() if k not in ("trial_id", "condition")})
        ordered_rows.append(ordered)

    output_path = ROOT / "master_trial_list.csv"
    write_csv(output_path, ordered_rows)
    print(f"\nWrote {len(ordered_rows)} merged, shuffled trials to {output_path}")

    example_path = ROOT / "instructions_example.csv"
    write_csv(example_path, ordered_rows[:1])
    print(f"Refreshed {example_path} from the merged list's first row ({ordered_rows[0]['painter']})")


if __name__ == "__main__":
    main()
