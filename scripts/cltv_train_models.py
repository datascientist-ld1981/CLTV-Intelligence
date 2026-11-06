from pathlib import Path
import pandas as pd
from lifetimes.utils import summary_data_from_transaction_data
from lifetimes import BetaGeoFitter, GammaGammaFitter

IN_PATH = Path("data/cleaned/invoice_level_clean.csv")
OUT_DIR = Path("data/model_output")
OUT_DIR.mkdir(parents=True, exist_ok=True)

CLTV_MONTHS = 6
PENALIZER = 0.01

print("Loading", IN_PATH)
tx = pd.read_csv(IN_PATH, parse_dates=["InvoiceDate"])
print("Invoices:", len(tx), "| Customers:", tx["CustomerID"].nunique())

# RFM-style summary for lifetimes
summary = summary_data_from_transaction_data(
    tx,
    customer_id_col="CustomerID",
    datetime_col="InvoiceDate",
    monetary_value_col="monetary_value",
    observation_period_end=tx["InvoiceDate"].max(),
)
print("Summary customers:", len(summary))
print("Repeat buyers:", (summary["frequency"] > 0).sum())

# BG/NBD — expected purchases
bgf = BetaGeoFitter(penalizer_coef=PENALIZER)
bgf.fit(summary["frequency"], summary["recency"], summary["T"])
print("BG/NBD params:", bgf.params_.to_dict())

horizon_days = CLTV_MONTHS * 30
summary = summary.copy()
summary["predicted_purchases"] = bgf.conditional_expected_number_of_purchases_up_to_time(
    horizon_days, summary["frequency"], summary["recency"], summary["T"]
)
summary["prob_alive"] = bgf.conditional_probability_alive(
    summary["frequency"], summary["recency"], summary["T"]
)

# Gamma-Gamma — expected order value (repeat buyers only)
returning = summary[(summary["frequency"] > 0) & (summary["monetary_value"] > 0)].copy()
ggf = GammaGammaFitter(penalizer_coef=PENALIZER)
ggf.fit(returning["frequency"], returning["monetary_value"])
print("Gamma-Gamma params:", ggf.params_.to_dict())

returning["expected_avg_order_value"] = ggf.conditional_expected_average_profit(
    returning["frequency"], returning["monetary_value"]
)

# CLTV
returning["clv"] = ggf.customer_lifetime_value(
    bgf,
    returning["frequency"],
    returning["recency"],
    returning["T"],
    returning["monetary_value"],
    time=CLTV_MONTHS,
    freq="D",
    discount_rate=0.01,
)

summary_path = OUT_DIR / "customer_summary_bg_nbd.csv"
clv_path = OUT_DIR / "customer_clv.csv"
top_path = OUT_DIR / "top_100_clv.csv"

summary.to_csv(summary_path)
returning.to_csv(clv_path)
returning.sort_values("clv", ascending=False).head(100).to_csv(top_path)

print("Saved:", summary_path)
print("Saved:", clv_path)
print("Saved:", top_path)
print("CLV mean:", round(returning["clv"].mean(), 2))
print("CLV median:", round(returning["clv"].median(), 2))
print("DONE")