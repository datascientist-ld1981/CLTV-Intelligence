import os
import pandas as pd
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)

FILE_PATH = os.path.join(
    ROOT_DIR, "data", "curated",
    "master_curated_transactions.csv"
)

REPORT_DIR = os.path.join(ROOT_DIR, "reports")
os.makedirs(REPORT_DIR, exist_ok=True)

# Read only the columns needed for this audit
header = pd.read_csv(FILE_PATH, nrows=0).columns.tolist()

possible_cols = [
    "order_id", "INVOICE_NUMBER", "SYS_INVOICE_NO",
    "transaction_date", "customer_id",
    "tender_customer_id", "CUSTOMER_Id2",
    "amount", "total_amount", "site",
    "INVOICE_TIME", "ORDER_TXN_CHANNEL"
]

usecols = [c for c in possible_cols if c in header]

id_cols = [
    c for c in usecols
    if c in [
        "order_id", "INVOICE_NUMBER", "SYS_INVOICE_NO",
        "customer_id", "tender_customer_id",
        "CUSTOMER_Id2", "site"
    ]
]

df = pd.read_csv(
    FILE_PATH,
    usecols=usecols,
    dtype={c: str for c in id_cols},
    low_memory=False
)

print("\n========== REVENUE RECONCILIATION ==========")

# Clean identifiers
for col in id_cols:
    df[col] = df[col].str.strip()

# Convert monetary columns
for col in ["amount", "total_amount"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

# 1. Group by order ID
invoice = df.groupby("order_id", dropna=False).agg(
    product_rows=("order_id", "size"),
    customer_count=("customer_id", "nunique"),
    amount_sum=("amount", "sum"),
    amount_min=("amount", "min"),
    amount_max=("amount", "max"),
    total_amount_min=("total_amount", "min"),
    total_amount_max=("total_amount", "max")
).reset_index()

# 2. Compare line-level amount sum against invoice total
invoice["amount_difference"] = (
    invoice["amount_sum"] - invoice["total_amount_max"]
)

invoice["amount_matches_total"] = np.isclose(
    invoice["amount_sum"],
    invoice["total_amount_max"],
    rtol=0,
    atol=0.01
)

print("\n1. REVENUE RECONCILIATION")
print("Unique orders:", len(invoice))
print("Amount matches total:",
      invoice["amount_matches_total"].sum())
print("Amount does not match total:",
      (~invoice["amount_matches_total"]).sum())

print(
    "Percentage matching:",
    round(invoice["amount_matches_total"].mean() * 100, 2),
    "%"
)

print("\n2. MULTIPLE CUSTOMER ID ORDERS")
multi_customer = invoice[invoice["customer_count"] > 1]

print("Orders with multiple customer IDs:", len(multi_customer))

# 3. Check other invoice identifiers and site
metadata_cols = [
    c for c in [
        "INVOICE_NUMBER", "SYS_INVOICE_NO",
        "site", "transaction_date"
    ] if c in df.columns
]

if metadata_cols:
    metadata = df.groupby("order_id").agg(
        **{
            f"{col}_unique": (col, "nunique")
            for col in metadata_cols
        }
    ).reset_index()

    invoice = invoice.merge(metadata, on="order_id", how="left")

# 4. Save audit reports
invoice.to_csv(
    os.path.join(REPORT_DIR, "invoice_reconciliation_summary.csv"),
    index=False
)

multi_customer.to_csv(
    os.path.join(REPORT_DIR, "multi_customer_invoice_summary.csv"),
    index=False
)

invoice[
    ~invoice["amount_matches_total"]
].head(500).to_csv(
    os.path.join(REPORT_DIR, "invoice_amount_mismatch_sample.csv"),
    index=False
)

print("\n3. AMOUNT MISMATCH EXAMPLES")
print(
    invoice[
        ~invoice["amount_matches_total"]
    ].head(15).to_string(index=False)
)

print("\nReports saved in:", REPORT_DIR)
print("\n========== RECONCILIATION COMPLETED ==========")