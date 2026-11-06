
from pathlib import Path
import pandas as pd

# Invoice we want to investigate
TARGET_ORDER = "10000008250520"

# Original source data folder
RAW_FOLDER = Path("data/raw")

# Possible transaction identifier columns
ID_COLUMNS = [
    "order_id",
    "INVOICE_NUMBER",
    "SYS_INVOICE_NO",
    "PROFORMA_INVOICE_NO"
]

found = False

# Search CSV files in chunks to avoid loading large files fully
for file in RAW_FOLDER.rglob("*.csv"):

    print(f"\nChecking: {file.name}")

    try:
        for chunk in pd.read_csv(
            file,
            dtype=str,
            chunksize=200000,
            low_memory=False
        ):

            matching_rows = pd.Series(False, index=chunk.index)

            for col in ID_COLUMNS:
                if col in chunk.columns:
                    matching_rows |= (
                        chunk[col].fillna("").str.strip()
                        == TARGET_ORDER
                    )

            result = chunk[matching_rows]

            if not result.empty:
                found = True

                print("\nMATCH FOUND IN:", file.name)
                print("Columns available:", result.columns.tolist())
                print(result.to_string(index=False))

                # Save the original matching rows
                output = Path("reports")
                output.mkdir(exist_ok=True)

                result.to_csv(
                    output / "source_invoice_10000008250520.csv",
                    index=False
                )

    except Exception as e:
        print("Could not read file:", file.name)
        print("Reason:", e)

if not found:
    print("\nInvoice was not found in the raw CSV files.")
else:
    print("\nInspection completed. Check the reports folder.")
