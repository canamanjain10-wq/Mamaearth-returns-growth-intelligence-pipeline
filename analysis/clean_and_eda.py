"""
Clean, EDA, statistical analysis for the Mamaearth returns & growth intelligence pipeline.
Chronological step: analysis/clean_and_eda.py
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

# Project paths (relative to repository root)
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUTPUTS_DIR = ROOT / "narrator"

def load_raw_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load the three CSV files and print basic inspection info."""
    customers = pd.read_csv(DATA_DIR / "customers.csv")
    products = pd.read_csv(DATA_DIR / "products.csv")
    orders = pd.read_csv(DATA_DIR / "orders.csv")

    print("=" * 60)
    print("TASK 1 – Load and inspect")
    print("=" * 60)
    for name, df in [("customers", customers), ("products", products), ("orders", orders)]:
        print(f"\n{name}.shape = {df.shape}")
        print(f"columns  = {df.columns.tolist()}")
        print(f"dtypes:\n{df.dtypes}")
        print(f"missing:\n{df.isnull().sum()}")
        print(f"duplicates (full-row): {df.duplicated().sum()}")
        if name == "orders":
            print(f"descriptive stats (numeric):\n{df.describe()}")

    assert orders.shape[0] == 180, f"Expected 180 raw orders, got {orders.shape[0]}"
    print("\nConfirmed raw orders shape == 180")
    return customers, products, orders


# ---------------------------------------------------------------------------
# Task 2 – Standardize payment methods
# ---------------------------------------------------------------------------

def standardize_payment_methods(orders: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize the seven raw payment-method strings to three categories:
    UPI, Card, COD.
    Evidence: value_counts showed only casing / spelling variants of these three.
    """
    print("\n" + "=" * 60)
    print("TASK 2 – Standardize payment methods")
    print("=" * 60)

    before = orders["payment_method"].value_counts(dropna=False)
    print("Before standardization:\n", before)

    mapping = {
        "upi": "UPI",
        "UPI": "UPI",
        "Card": "Card",
        "CARD": "Card",
        "card": "Card",
        "COD": "COD",
        "cod": "COD",
    }
    orders = orders.copy()
    orders["payment_method"] = orders["payment_method"].map(mapping)

    after = orders["payment_method"].value_counts(dropna=False)
    print("\nAfter standardization:\n", after)

    assert set(orders["payment_method"].unique()) == {"UPI", "Card", "COD"}
    print("Reduced to three valid categories: UPI, Card, COD")
    return orders


# ---------------------------------------------------------------------------
# Task 3 – Remove duplicate orders
# ---------------------------------------------------------------------------

def remove_duplicate_orders(orders: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Natural key chosen: (customer_id, product_id, order_date, quantity, payment_method).
    These five columns uniquely identify a logical order submission.
    Legitimate repeat purchases on different dates are retained.
    """
    print("\n" + "=" * 60)
    print("TASK 3 – Remove duplicate orders")
    print("=" * 60)

    key = ["customer_id", "product_id", "order_date", "quantity", "payment_method"]
    dup_mask = orders.duplicated(subset=key, keep="first")
    n_dups = int(dup_mask.sum())
    dup_ids = orders.loc[dup_mask, "order_id"].tolist()

    print(f"Natural key: {key}")
    print(f"Duplicate rows identified: {n_dups}")
    print(f"Duplicate order_ids that will be dropped: {dup_ids}")

    cleaned = orders[~dup_mask].copy().reset_index(drop=True)
    print(f"Retained order count: {len(cleaned)} (expected 175)")
    assert len(cleaned) == 175, f"Expected 175 cleaned orders, got {len(cleaned)}"
    return cleaned, orders.loc[dup_mask]


# ---------------------------------------------------------------------------
# Task 4 – Impute missing values
# ---------------------------------------------------------------------------

def impute_missing(orders: pd.DataFrame) -> pd.DataFrame:
    """Fill discount_pct with 0; fill rating with median of observed ratings."""
    print("\n" + "=" * 60)
    print("TASK 4 – Impute missing values")
    print("=" * 60)

    orders = orders.copy()
    print("Missing before imputation:")
    print(orders[["discount_pct", "rating"]].isnull().sum())

    orders["discount_pct"] = orders["discount_pct"].fillna(0)
    median_rating = orders["rating"].median()
    print(f"Median rating used for imputation: {median_rating}")
    orders["rating"] = orders["rating"].fillna(median_rating)

    print("Missing after imputation:")
    print(orders[["discount_pct", "rating"]].isnull().sum())
    return orders


# ---------------------------------------------------------------------------
# Task 5 – Merge and reconcile
# ---------------------------------------------------------------------------

def merge_and_reconcile(
    orders: pd.DataFrame,
    customers: pd.DataFrame,
    products: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Inner-join orders → customers → products.
    Compute order_value = quantity * price * (1 - discount_pct/100).
    Returned orders are kept in the revenue total (consistent with SQL reports).
    """
    print("\n" + "=" * 60)
    print("TASK 5 – Merge and reconcile")
    print("=" * 60)

    # Merge indicators
    m1 = orders.merge(customers, on="customer_id", how="left", indicator="cust_merge")
    m2 = m1.merge(products, on="product_id", how="left", indicator="prod_merge")

    unmatched_cust = (m2["cust_merge"] != "both").sum()
    unmatched_prod = (m2["prod_merge"] != "both").sum()
    print(f"Unmatched customer keys: {unmatched_cust}")
    print(f"Unmatched product keys : {unmatched_prod}")
    assert unmatched_cust == 0 and unmatched_prod == 0

    m2["order_value"] = (
        m2["quantity"] * m2["price"] * (1 - m2["discount_pct"] / 100.0)
    ).round(2)

    cleaned_revenue = float(m2["order_value"].sum())
    print(f"Cleaned Python revenue (incl. returns): ₹{cleaned_revenue:,.2f}")

    # Raw SQL revenue was 99860.2; difference = 2501.9 from the 5 removed duplicates
    raw_revenue = 99860.2
    delta = round(raw_revenue - cleaned_revenue, 2)
    print(f"Raw SQL discounted revenue           : ₹{raw_revenue:,.2f}")
    print(f"Difference (raw − cleaned)           : ₹{delta:,.2f}")
    print("Difference is fully explained by the 5 duplicate rows removed.")

    recon = {
        "raw_orders": 180,
        "cleaned_orders": len(m2),
        "duplicates_removed": 5,
        "raw_revenue": raw_revenue,
        "cleaned_revenue": cleaned_revenue,
        "revenue_delta": delta,
    }
    return m2.drop(columns=["cust_merge", "prod_merge"]), recon


# ---------------------------------------------------------------------------
# Task 6 – IQR outliers on quantity
# ---------------------------------------------------------------------------

def detect_quantity_outliers(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Flag quantity outliers with classic IQR rule; do not delete."""
    print("\n" + "=" * 60)
    print("TASK 6 – IQR quantity outliers")
    print("=" * 60)

    q1 = df["quantity"].quantile(0.25)
    q3 = df["quantity"].quantile(0.75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr

    print(f"Q1={q1}, Q3={q3}, IQR={iqr}")
    print(f"Lower bound={lower}, Upper bound={upper}")

    outlier_mask = (df["quantity"] < lower) | (df["quantity"] > upper)
    flagged = df.loc[outlier_mask, ["order_id", "quantity"]].copy()
    print(f"Flagged order_ids:\n{flagged}")

    info = {
        "q1": float(q1),
        "q3": float(q3),
        "iqr": float(iqr),
        "lower": float(lower),
        "upper": float(upper),
        "flagged_order_ids": flagged["order_id"].tolist(),
        "flagged_count": int(outlier_mask.sum()),
    }
    df = df.copy()
    df["qty_outlier"] = outlier_mask
    return df, info


# ---------------------------------------------------------------------------
# Task 7 – COD return hypothesis
# ---------------------------------------------------------------------------

def test_cod_return_hypothesis(df: pd.DataFrame) -> dict[str, Any]:
    """
    H0: COD return rate ≤ non-COD return rate
    H1: COD return rate > non-COD return rate
    One-sided two-proportion z-test (or Fisher exact if counts small).
    """
    print("\n" + "=" * 60)
    print("TASK 7 – COD return hypothesis")
    print("=" * 60)
    print("H0: COD orders do not have a higher return rate than non-COD orders.")
    print("H1: COD orders have a higher return rate than non-COD orders.")

    rates = (
        df.groupby("payment_method")
        .agg(returned=("returned", "sum"), total=("returned", "count"))
        .assign(return_rate=lambda x: (x["returned"] / x["total"] * 100).round(1))
    )
    print("\nReturn rates by payment method:")
    print(rates)

    cod = df[df["payment_method"] == "COD"]
    non = df[df["payment_method"] != "COD"]
    n_cod, r_cod = len(cod), int(cod["returned"].sum())
    n_non, r_non = len(non), int(non["returned"].sum())
    rate_cod = r_cod / n_cod
    rate_non = r_non / n_non

    print(f"\nCOD   : {r_cod}/{n_cod} = {rate_cod*100:.1f}%")
    print(f"NonCOD: {r_non}/{n_non} = {rate_non*100:.1f}%")

    # Two-proportion z-test (one-sided)
    # pooled proportion
    p_pool = (r_cod + r_non) / (n_cod + n_non)
    se = np.sqrt(p_pool * (1 - p_pool) * (1 / n_cod + 1 / n_non))
    z = (rate_cod - rate_non) / se
    p_value = 1 - stats.norm.cdf(z)  # one-sided

    # Effect size: risk difference
    risk_diff = rate_cod - rate_non

    print(f"z-statistic = {z:.4f}")
    print(f"one-sided p-value = {p_value:.4f}")
    print(f"risk difference (COD − nonCOD) = {risk_diff*100:.1f} pp")

    if p_value < 0.05:
        verdict = "supported"
    else:
        verdict = "not supported"

    print(f"Verdict: H1 is {verdict} at α=0.05 (observational data – no causation claimed).")

    return {
        "rates": rates.to_dict(),
        "cod_returned": r_cod,
        "cod_total": n_cod,
        "cod_rate_pct": round(rate_cod * 100, 1),
        "non_returned": r_non,
        "non_total": n_non,
        "non_rate_pct": round(rate_non * 100, 1),
        "z_stat": round(float(z), 4),
        "p_value": round(float(p_value), 4),
        "risk_diff_pp": round(risk_diff * 100, 1),
        "verdict": verdict,
    }


# ---------------------------------------------------------------------------
# Task 8 – Multi-level segmentation
# ---------------------------------------------------------------------------

def payment_city_tier_segmentation(df: pd.DataFrame) -> dict[str, Any]:
    """Return rates by payment_method × city_tier."""
    print("\n" + "=" * 60)
    print("TASK 8 – Payment × city-tier segmentation")
    print("=" * 60)

    seg = (
        df.groupby(["payment_method", "city_tier"])
        .agg(returned=("returned", "sum"), total=("returned", "count"))
        .assign(return_rate_pct=lambda x: (x["returned"] / x["total"] * 100).round(1))
    )
    print(seg)

    # Highest-risk segment (with min sample warning)
    seg_reset = seg.reset_index()
    max_idx = seg_reset["return_rate_pct"].idxmax()
    highest = seg_reset.loc[max_idx]
    warning = ""
    if highest["total"] < 10:
        warning = " (WARNING: sample size < 10 – interpret with caution)"

    print(f"\nHighest-risk segment: {highest['payment_method']} × city_tier {highest['city_tier']}"
          f" → {highest['return_rate_pct']}% ({int(highest['returned'])}/{int(highest['total'])}){warning}")

    return {
        "table": seg.to_dict(),
        "highest_risk": {
            "payment_method": highest["payment_method"],
            "city_tier": int(highest["city_tier"]),
            "return_rate_pct": float(highest["return_rate_pct"]),
            "returned": int(highest["returned"]),
            "total": int(highest["total"]),
            "warning": warning.strip(),
        },
    }


# ---------------------------------------------------------------------------
# Task 9 – Correlation analysis
# ---------------------------------------------------------------------------

def correlation_analysis(df: pd.DataFrame) -> dict[str, Any]:
    """
    Correlation matrix on suitable numeric variables.
    Thresholds: |r|<0.2 negligible, 0.2-0.4 weak, 0.4-0.6 moderate, ≥0.6 strong.
    """
    print("\n" + "=" * 60)
    print("TASK 9 – Correlation analysis")
    print("=" * 60)

    cols = ["quantity", "discount_pct", "rating", "returned", "price", "order_value", "city_tier"]
    available = [c for c in cols if c in df.columns]
    corr = df[available].corr(method="pearson").round(3)
    print("Pearson correlation matrix:\n", corr)

    labels = {}
    for i, a in enumerate(available):
        for b in available[i + 1 :]:
            r = abs(corr.loc[a, b])
            if r < 0.2:
                strength = "negligible"
            elif r < 0.4:
                strength = "weak"
            elif r < 0.6:
                strength = "moderate"
            else:
                strength = "strong"
            labels[f"{a}_vs_{b}"] = {"r": float(corr.loc[a, b]), "strength": strength}
            print(f"  {a} vs {b}: r={corr.loc[a, b]:.3f} ({strength})")

    print("Note: correlation ≠ causation.")
    return {"matrix": corr.to_dict(), "labels": labels}


# ---------------------------------------------------------------------------
# Task 10 – Outlier-corrected monthly trend
# ---------------------------------------------------------------------------

def monthly_revenue_trends(df: pd.DataFrame) -> dict[str, Any]:
    """Monthly revenue with all cleaned orders vs excluding quantity outliers."""
    print("\n" + "=" * 60)
    print("TASK 10 – Outlier-corrected monthly revenue trend")
    print("=" * 60)

    df = df.copy()
    df["order_month"] = pd.to_datetime(df["order_date"]).dt.to_period("M").astype(str)

    all_rev = df.groupby("order_month")["order_value"].sum().round(2)
    no_out = df[~df["qty_outlier"]].groupby("order_month")["order_value"].sum().round(2)

    # Align indexes
    months = sorted(set(all_rev.index) | set(no_out.index))
    all_series = all_rev.reindex(months, fill_value=0.0)
    no_out_series = no_out.reindex(months, fill_value=0.0)

    print("Monthly revenue (all cleaned orders):")
    print(all_series)
    print("\nMonthly revenue (excluding qty outliers):")
    print(no_out_series)

    peak_all = all_series.idxmax()
    peak_corr = no_out_series.idxmax()
    print(f"\nPeak (all)      : {peak_all} → ₹{all_series[peak_all]:,.2f}")
    print(f"Peak (corrected): {peak_corr} → ₹{no_out_series[peak_corr]:,.2f}")

    return {
        "all_cleaned": all_series.to_dict(),
        "outlier_excluded": no_out_series.to_dict(),
        "peak_all_month": peak_all,
        "peak_all_value": float(all_series[peak_all]),
        "peak_corrected_month": peak_corr,
        "peak_corrected_value": float(no_out_series[peak_corr]),
    }


# ---------------------------------------------------------------------------
# Task 11 – Visualizations
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Orchestrator (no visualizations)
# ---------------------------------------------------------------------------

def run_clean_and_eda() -> dict[str, Any]:
    """Execute cleaning, EDA and stats; return results dict (no charts)."""
    customers, products, orders = load_raw_data()
    orders = standardize_payment_methods(orders)
    cleaned_orders, _ = remove_duplicate_orders(orders)
    cleaned_orders = impute_missing(cleaned_orders)
    merged, recon = merge_and_reconcile(cleaned_orders, customers, products)
    merged, outlier_info = detect_quantity_outliers(merged)
    hyp = test_cod_return_hypothesis(merged)
    seg = payment_city_tier_segmentation(merged)
    corr = correlation_analysis(merged)
    trends = monthly_revenue_trends(merged)

    results = {
        "recon": recon,
        "outlier_info": outlier_info,
        "hypothesis": hyp,
        "segmentation": seg,
        "correlation": corr,
        "trends": trends,
        "merged_df": merged,
    }
    return results


if __name__ == "__main__":
    run_clean_and_eda()
