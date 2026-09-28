"""
Builds a reproducible patient subset from the full Synthea CSV export.

Randomly samples SAMPLE_SIZE patients (fixed seed for reproducibility) and
filters every patient-linked table down to that cohort. Organisations and
providers are copied as-is since they are small reference tables shared
across the whole population.
"""

import argparse
import os

import pandas as pd

SAMPLE_SIZE = 5000
RANDOM_SEED = 42
CHUNK_SIZE = 200_000

PATIENT_LINKED_FILES = [
    "encounters.csv",
    "conditions.csv",
    "medications.csv",
    "procedures.csv",
    "immunizations.csv",
]
COPY_AS_IS_FILES = ["organizations.csv", "providers.csv"]


def parse_args():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir",
        default=os.path.join(repo_root, "data", "raw"),
        help="Directory containing the full Synthea CSV export (default: data/raw)",
    )
    parser.add_argument(
        "--output-dir",
        default=os.path.join(repo_root, "data", "subset"),
        help="Directory to write the sampled subset to (default: data/subset)",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=SAMPLE_SIZE,
        help=f"Number of patients to sample (default: {SAMPLE_SIZE})",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=RANDOM_SEED,
        help=f"Random seed for reproducibility (default: {RANDOM_SEED})",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    in_dir = args.input_dir
    out_dir = args.output_dir

    def in_path(name):
        return os.path.join(in_dir, name)

    def out_path(name):
        return os.path.join(out_dir, name)

    os.makedirs(out_dir, exist_ok=True)

    print("Step 1: Loading patients.csv ...")
    patients = pd.read_csv(in_path("patients.csv"))
    total_patients = len(patients)
    print(f"  Total patients available: {total_patients:,}")

    sample_size = min(args.sample_size, total_patients)
    patients_subset = patients.sample(n=sample_size, random_state=args.seed)
    patient_ids = set(patients_subset["Id"])

    patients_subset.to_csv(out_path("patients.csv"), index=False)
    print(f"  Kept {sample_size:,} patients -> {out_path('patients.csv')}")

    for filename in PATIENT_LINKED_FILES:
        print(f"Step: Filtering {filename} ...")
        dest = out_path(filename)
        kept_rows = 0
        first_chunk = True
        for chunk in pd.read_csv(in_path(filename), chunksize=CHUNK_SIZE):
            filtered = chunk[chunk["PATIENT"].isin(patient_ids)]
            kept_rows += len(filtered)
            filtered.to_csv(dest, mode="w" if first_chunk else "a", header=first_chunk, index=False)
            first_chunk = False
        if first_chunk:
            # No rows were ever read; still write an empty file with header via a fresh read
            pd.read_csv(in_path(filename), nrows=0).to_csv(dest, index=False)
        print(f"  Kept {kept_rows:,} rows -> {dest}")

    for filename in COPY_AS_IS_FILES:
        print(f"Step: Copying {filename} as-is ...")
        df = pd.read_csv(in_path(filename))
        df.to_csv(out_path(filename), index=False)
        print(f"  Copied {len(df):,} rows -> {out_path(filename)}")

    print("Done. Subset written to:", out_dir)


if __name__ == "__main__":
    main()
