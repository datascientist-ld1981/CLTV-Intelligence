from pathlib import Path
import numpy as np
import pandas as pd

RAW_DIR = Path("data/raw")
OUT_DIR = Path("data/cleaned")
OUT_DIR.mkdir(parents=True, exist_ok=True)

files = sorted(RAW_DIR.rglob("*.csv"))
print("Files found:", len(files))
for f in files:
    print(" ", f)

if not files:
    raise SystemExit("No CSV files in data/raw")

cols = ["CUSTOMER_Id2", "INVOICE_NUMBER", "INVOICE_DATE", "total_amount"]
frames = []
for f in files:
    print("Loading", f)
    df = pd.read_csv(f, usecols=cols, low_memory=False)
    df["__source_file"] = str(f)
    frames.append(df)

raw = pd.concat(frames, ignore_index=True)
print("Line rows:", len(raw))

raw["CUSTOMER_Id2"] = pd.to_numeric(raw["CUSTOMER_Id2"], errors="coerce")
raw["INVOICE_NUMBER"] = raw["INVOICE_NUMBER"].astype(str).str.strip()
raw.loc[raw["INVOICE_NUMBER"].isin(["", "nan", "None", "<NA>"]), "INVOICE_NUMBER"] = np.nan
raw["INVOICE_DATE"] = pd.to_datetime(raw["INVOICE_DATE"], errors="coerce")
raw["total_amount"] = pd.to_numeric(raw["total_amount"], errors="coerce")

raw = raw.dropna(subset=["CUSTOMER_Id2", "INVOICE_NUMBER", "INVOICE_DATE"])

tx = (
    raw.groupby(["CUSTOMER_Id2", "INVOICE_NUMBER"], as_index=False)
    .agg(InvoiceDate=("INVOICE_DATE", "min"), monetary_value=("total_amount", "max"))
    .rename(columns={"CUSTOMER_Id2": "CustomerID", "INVOICE_NUMBER": "InvoiceNo"})
)
tx = tx[tx["monetary_value"] >= 0.01]

out = OUT_DIR / "invoice_level_clean.csv"
tx.to_csv(out, index=False)
print("Saved:", out)
print("Invoices:", len(tx), "| Customers:", tx["CustomerID"].nunique())
print("DONE")