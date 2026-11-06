import os
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)

FILE_PATH = os.path.join(
    ROOT_DIR, "data", "curated",
    "master_curated_transactions.csv"
)

OUTPUT_DIR = os.path.join(ROOT_DIR, "reports")
os.makedirs(OUTPUT_DIR, exist_ok=True)

df = pd.read_csv(FILE_PATH, low_memory=False)

print("\n========== INVOICE AND REVENUE AUDIT ==========")

# 1. Identify relevant columns
print("\n1. RELEVANT COLUMNS")

for col in df.columns:
    if any(word in col.lower() for word in
           ["amount", "total", "invoice", "order", "date", "customer"]):
        print(col)

# 2. Identify invoice column
invoice_col = "order_id"

if invoice_col not in df.columns:
    raise ValueError("order_id column not found.")

# 3. Inspect available amount columns
amount_cols = [
    c for c in df.columns
    if any(word in c.lower() for word in ["amount", "total"])
]

for col in amount_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

print("\n2. AMOUNT COLUMN SUMMARY")

print(df[amount_cols].describe().to_string())

# 4. Invoice-level analysis
agg = {
    "product_rows": (invoice_col, "size"),
    "unique_customers": ("customer_id", "nunique")
}

for col in amount_cols:
    agg[f"{col}_sum"] = (col, "sum")
    agg[f"{col}_min"] = (col, "min")
    agg[f"{col}_max"] = (col, "max")

invoice_audit = (
    df.groupby(invoice_col, dropna=False)
      .agg(**agg)
      .reset_index()
)

print("\n3. INVOICE SUMMARY")
print(invoice_audit.describe().to_string())

print("\n4. INVOICES WITH MULTIPLE PRODUCT ROWS")
print(
    invoice_audit[
        invoice_audit["product_rows"] > 1
    ].head(15).to_string(index=False)
)

print("\n5. INVOICES WITH MORE THAN ONE CUSTOMER ID")
print(
    invoice_audit[
        invoice_audit["unique_customers"] > 1
    ].head(15).to_string(index=False)
)

# 6. Save audit outputs
invoice_audit.head(100).to_csv(
    os.path.join(OUTPUT_DIR, "invoice_audit_sample.csv"),
    index=False
)

invoice_audit.to_csv(
    os.path.join(OUTPUT_DIR, "invoice_audit_full.csv"),
    index=False
)

print("\nAudit files saved in:", OUTPUT_DIR)
print("\n========== AUDIT COMPLETED ==========")