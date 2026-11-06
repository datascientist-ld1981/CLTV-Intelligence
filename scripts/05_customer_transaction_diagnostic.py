import os
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)

FILE_PATH = os.path.join(
    ROOT_DIR,
    "data",
    "curated",
    "master_curated_transactions.csv"
)

df = pd.read_csv(FILE_PATH, low_memory=False)

print("\n========== CUSTOMER DIAGNOSTIC ==========")

# Customer ID distribution
print("\n1. CUSTOMER ID CHECK")

print("Total rows:", len(df))
print("Unique customers:", df["customer_id"].nunique())

print(
    "Rows with customer ID 0:",
    df["customer_id"].astype(str).str.strip().isin(["0", "0.0"]).sum()
)

# Identify invoice column
invoice_col = next(
    (c for c in ["order_id", "INVOICE_NUMBER", "SYS_INVOICE_NO"]
     if c in df.columns),
    None
)

if invoice_col:

    print("\n2. INVOICE ANALYSIS")

    print("Invoice column:", invoice_col)

    print("Unique invoices:", df[invoice_col].nunique())

    print(
        "Rows per invoice:"
    )

    print(df.groupby(invoice_col).size().describe())

    # Purchase count per customer
    valid = df[
        df["customer_id"].notna()
        & ~df["customer_id"].astype(str).str.strip().isin(["0", "0.0", ""])
    ].copy()

    valid["customer_id"] = valid["customer_id"].astype(str)

    print("\n3. ROW COUNT VS DISTINCT INVOICE COUNT")

    comparison = valid.groupby("customer_id").agg(
        product_rows=(invoice_col, "size"),
        distinct_invoices=(invoice_col, "nunique")
    )

    print(comparison.head(20))

    print("\nTotal product rows:", comparison["product_rows"].sum())

    print(
        "Total customer-invoice combinations:",
        comparison["distinct_invoices"].sum()
    )

else:
    print("\nNo invoice identifier found.")

print("\n========== DIAGNOSTIC COMPLETED ==========")