
import pandas as pd
from pathlib import Path

TARGET_ORDER_ID = "10000008250520"

RAW_FOLDER = Path("data/raw")

files = list(RAW_FOLDER.rglob("*.csv"))

print(f"Total CSV files to inspect: {len(files)}")

found = False

for file in files:

    print(f"\nChecking: {file.name}")

    try:
        for chunk in pd.read_csv(
            file,
            dtype=str,
            chunksize=200000,
            keep_default_na=False,
            on_bad_lines="warn"
        ):

            # Check whether order_id exists
            if "order_id" not in chunk.columns:
                continue

            matching_rows = chunk[
                chunk["order_id"].str.strip() == TARGET_ORDER_ID
            ]

            if not matching_rows.empty:

                found = True

                print("\n" + "=" * 70)
                print("MATCH FOUND")
                print("SOURCE FILE:", file.name)
                print("=" * 70)

                print(matching_rows.to_string(index=False))

    except Exception as e:
        print(f"Error reading {file.name}: {e}")

if not found:
    print("\nInvoice not found in the original CSV files.")
