"""
================================================================================
Stage 8: Enterprise CLTV Intelligence System
Data Platform Layer: Automated Multi-Batch Ingestion & Data Cleaning Pipeline
================================================================================

This module handles:
1. Recursive crawling of raw temporal directories (e.g., 2024, 2025, 2026).
2. Dynamic column schema mapping (resolving legacy variations like CUSTOMER_Id2 vs customer_id).
3. Handling UTF-8 BOM encoding and file format differences across large split CSVs.
4. Cleansing null IDs, standardizing ISO dates, and filtering negative spend/refund errors.
5. Consolidated exports to curated Master Data and Point-in-Time Feature Store tables.
"""

import os
import glob
import pandas as pd
import numpy as np


def run_production_cleaning_pipeline(raw_dir: str, curated_dir: str) -> None:
    """
    Crawls raw data directories, standardizes column aliases across multi-year files,
    cleans missing identifiers and invalid amounts, deduplicates records, and exports 
    unified curated golden tables.

    Args:
        raw_dir (str): Path to directory containing raw batch data.
        curated_dir (str): Path to directory where cleaned outputs will be saved.
    """
    raw_dir = os.path.abspath(raw_dir)
    curated_dir = os.path.abspath(curated_dir)

    print(f"🔍 Crawling raw temporal batch directories in: {raw_dir}")

    # Discover all raw CSV and Excel files recursively
    search_patterns = [
        os.path.join(raw_dir, "**", "*.csv"),
        os.path.join(raw_dir, "**", "*.xlsx")
    ]
    
    file_list = []
    for pattern in search_patterns:
        file_list.extend(glob.glob(pattern, recursive=True))
        
    if not file_list:
        print(f"❌ Error: No raw data files found in '{raw_dir}'!")
        return

    print(f"🚀 Found {len(file_list)} raw batch files. Starting automated ingestion...\n")
    
    cleaned_frames = []
    audit_records = []
    
    for file_path in sorted(file_list):
        file_name = os.path.basename(file_path)
        folder_name = os.path.basename(os.path.dirname(file_path))
        
        try:
            # 1. READ FILE: Use utf-8-sig to automatically strip Byte Order Mark (\ufeff) headers
            if file_path.endswith('.csv'):
                df_raw = pd.read_csv(file_path, low_memory=False, encoding='utf-8-sig')
            else:
                df_raw = pd.read_excel(file_path)
                
            raw_count = len(df_raw)
            if raw_count == 0:
                print(f"⚠️ Skipping empty file: {file_name}")
                continue

            # Clean and normalize header strings
            cols_map = {col: str(col).replace('\ufeff', '').strip() for col in df_raw.columns}
            df_raw = df_raw.rename(columns=cols_map)
            cols_lower = {c.lower(): c for c in df_raw.columns}
            
            # 2. RESOLVE CUSTOMER ID: Priority cascade across historical schema variants
            cust_col = None
            for c_alias in ['customer_id', 'customer_id2', 'tender_customer_id', 'mbr_ind_id', 'cust_id', 'user_id']:
                if c_alias in cols_lower:
                    cust_col = cols_lower[c_alias]
                    break
                    
            if not cust_col:
                print(f"⚠️ Skipping {file_name}: No valid Customer ID column identified.")
                continue
                
            df_raw = df_raw.rename(columns={cust_col: 'customer_id'})
            
            # Filter null or empty string customer identifiers
            df_clean = df_raw.dropna(subset=['customer_id']).copy()
            df_clean['customer_id'] = df_clean['customer_id'].astype(str).str.strip()
            df_clean = df_clean[df_clean['customer_id'] != '']

            # 3. RESOLVE TRANSACTION DATE: Map INVOICE_DATE or transaction_date to ISO format
            date_col = None
            for d_alias in ['invoice_date', 'transaction_date', 'updtd_tmstp', 'date']:
                if d_alias in cols_lower:
                    date_col = cols_lower[d_alias]
                    break
                    
            if date_col:
                if date_col != 'transaction_date':
                    df_clean = df_clean.rename(columns={date_col: 'transaction_date'})
                df_clean['transaction_date'] = pd.to_datetime(df_clean['transaction_date'], errors='coerce')
                df_clean = df_clean.dropna(subset=['transaction_date'])

            # 4. RESOLVE TRANSACTION AMOUNT: Map line-item (item_total_amount) or invoice total
            amt_col = None
            for a_alias in ['item_total_amount', 'total_amount', 'amount', 'amt']:
                if a_alias in cols_lower:
                    amt_col = cols_lower[a_alias]
                    break
                    
            if amt_col:
                if amt_col != 'amount':
                    df_clean = df_clean.rename(columns={amt_col: 'amount'})
                df_clean['amount'] = pd.to_numeric(df_clean['amount'], errors='coerce')
                # Retain positive revenue transactions
                df_clean = df_clean[df_clean['amount'] > 0]

            # 5. RESOLVE CHANNEL CATEGORY
            if 'ORDER_TXN_CHANNEL' in df_clean.columns:
                df_clean['channel'] = df_clean['ORDER_TXN_CHANNEL'].fillna('STORE').astype(str).str.upper().str.strip()
            elif 'STORE_TYPE' in df_clean.columns:
                df_clean['channel'] = df_clean['STORE_TYPE'].fillna('STORE').astype(str).str.upper().str.strip()
            else:
                df_clean['channel'] = 'RETAIL_STORE'

            # 6. DEDUPLICATE: Deduplicate by primary transaction key if present
            txn_id_col = 'order_id' if 'order_id' in df_clean.columns else ('INVOICE_NUMBER' if 'INVOICE_NUMBER' in df_clean.columns else None)
            if txn_id_col:
                df_clean = df_clean.drop_duplicates(subset=[txn_id_col, 'customer_id'])
                
            clean_count = len(df_clean)
            
            audit_records.append({
                'Folder': folder_name,
                'File': file_name,
                'Raw Rows': raw_count,
                'Clean Rows': clean_count,
                'Dropped Rows': raw_count - clean_count
            })
            
            cleaned_frames.append(df_clean)
            print(f"✅ Processed [{folder_name}] {file_name}: {raw_count:,} raw ➔ {clean_count:,} clean rows")
            
        except Exception as e:
            print(f"❌ Error processing '{file_name}': {str(e)}")
            continue

    if not cleaned_frames:
        print("\n❌ Error: No datasets were successfully cleaned.")
        return
        
    # =========================================================================
    # EXPORT MASTER GOLDEN TABLE (LAYER 1 DATA PLATFORM)
    # =========================================================================
    master_df = pd.concat(cleaned_frames, ignore_index=True)
    if 'transaction_date' in master_df.columns:
        master_df = master_df.sort_values(by='transaction_date').reset_index(drop=True)
    
    os.makedirs(curated_dir, exist_ok=True)
    master_path = os.path.join(curated_dir, "master_curated_transactions.csv")
    master_df.to_csv(master_path, index=False)
    
    # =========================================================================
    # EXPORT POINT-IN-TIME FEATURE STORE TABLE
    # =========================================================================
    if 'transaction_date' in master_df.columns and 'amount' in master_df.columns:
        snapshot_date = master_df['transaction_date'].max()
        
        feature_store = master_df.groupby('customer_id').agg(
            recency_days=('transaction_date', lambda x: (snapshot_date - x.max()).days),
            frequency_orders=('amount', 'count'),
            monetary_spend=('amount', 'sum'),
            avg_order_value=('amount', 'mean'),
            first_purchase=('transaction_date', 'min'),
            last_purchase=('transaction_date', 'max')
        ).reset_index()
        
        feature_path = os.path.join(curated_dir, "customer_feature_store.csv")
        feature_store.to_csv(feature_path, index=False)
    
    # Print execution summary log
    print("\n" + "=" * 80)
    print("FINAL RECOVERED INGESTION AUDIT SUMMARY")
    print("=" * 80)
    print(pd.DataFrame(audit_records).to_string(index=False))
    print("=" * 80)
    print(f"\n🎉 Total Unified Clean Transactions: {len(master_df):,}")
    print(f"🎉 Total Golden Customers in Feature Store: {len(feature_store):,}")


if __name__ == "__main__":
    # Dynamically resolve root project folder path
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    
    if os.path.exists(os.path.join(SCRIPT_DIR, "data", "raw")):
        ROOT_DIR = SCRIPT_DIR
    else:
        ROOT_DIR = os.path.dirname(SCRIPT_DIR)
        
    RAW_PATH = os.path.join(ROOT_DIR, "data", "raw")
    CURATED_PATH = os.path.join(ROOT_DIR, "data", "curated")
    
    run_production_cleaning_pipeline(RAW_PATH, CURATED_PATH)