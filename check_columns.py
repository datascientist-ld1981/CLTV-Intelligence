import os
import glob
import pandas as pd

def inspect_column_mismatches(raw_dir: str):
    raw_dir = os.path.abspath(raw_dir)
    print(f"🔍 Inspecting files inside: {raw_dir}\n")

    search_patterns = [
        os.path.join(raw_dir, "**", "*.csv"),
        os.path.join(raw_dir, "**", "*.xlsx")
    ]
    
    file_list = []
    for pattern in search_patterns:
        file_list.extend(glob.glob(pattern, recursive=True))
        
    if not file_list:
        print("❌ No raw CSV or Excel files found!")
        print(f"Checked path: {raw_dir}")
        print("Please check if your files are inside the 'data/raw' folder of your project.")
        return

    # Standard expected canonical columns
    CUST_ALIASES = {'customer_id', 'cust_id', 'customerid', 'client_id', 'user_id', 'account_id', 'member_id', 'cust_no'}
    DATE_ALIASES = {'transaction_date', 'date', 'txn_date', 'order_date', 'timestamp', 'time'}
    AMT_ALIASES = {'amount', 'amt', 'price', 'spend', 'val', 'transaction_amount', 'total_amount'}

    print("=" * 110)
    print(f"{'FOLDER / FILE NAME':<40} | {'STATUS':<8} | {'DETECTED COLUMNS & MISMATCH DIAGNOSTICS'}")
    print("=" * 110)

    for file_path in sorted(file_list):
        file_name = os.path.basename(file_path)
        folder_name = os.path.basename(os.path.dirname(file_path))
        file_label = f"[{folder_name}] {file_name}"
        
        try:
            if file_path.endswith('.csv'):
                df_sample = pd.read_csv(file_path, nrows=1, encoding='utf-8-sig')
            else:
                df_sample = pd.read_excel(file_path, nrows=1)
                
            cols = [str(c).replace('\ufeff', '').strip() for c in df_sample.columns]
            cols_lower = [c.lower() for c in cols]
            
            # Check presence of primary functional fields
            found_cust = any(c in CUST_ALIASES for c in cols_lower)
            found_date = any(c in DATE_ALIASES for c in cols_lower)
            found_amt = any(c in AMT_ALIASES for c in cols_lower)
            
            issues = []
            if not found_cust:
                issues.append("❌ Missing Customer ID")
            if not found_date:
                issues.append("⚠️ Missing Date")
            if not found_amt:
                issues.append("⚠️ Missing Amount")
                
            status_flag = "✅ OK" if (found_cust and found_date and found_amt) else ("❌ CRITICAL" if not found_cust else "⚠️ WARN")
            
            diag_str = f"Cols: {cols}"
            if issues:
                diag_str += f" | Issues: {', '.join(issues)}"
                
            print(f"{file_label:<40} | {status_flag:<8} | {diag_str}")
            
        except Exception as e:
            print(f"{file_label:<40} | ❌ ERROR  | Could not read file: {str(e)}")

    print("=" * 110)

if __name__ == "__main__":
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    
    # Check if data/raw exists directly in current script folder first
    local_raw = os.path.join(SCRIPT_DIR, "data", "raw")
    parent_raw = os.path.join(os.path.dirname(SCRIPT_DIR), "data", "raw")
    
    if os.path.exists(local_raw):
        RAW_PATH = local_raw
    elif os.path.exists(parent_raw):
        RAW_PATH = parent_raw
    else:
        RAW_PATH = local_raw

    inspect_column_mismatches(RAW_PATH)