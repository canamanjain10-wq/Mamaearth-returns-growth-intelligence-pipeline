"""Generate narrator/findings.json from verified analysis results."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_DIR = ROOT / "narrator"


def build_findings(results: dict[str, Any]) -> dict[str, Any]:
    """Construct a structured findings dictionary from analysis results."""
    recon = results["recon"]
    hyp = results["hypothesis"]
    seg = results["segmentation"]
    corr = results["correlation"]
    trends = results["trends"]
    outlier = results["outlier_info"]

    findings = {
        "project": "Mamaearth returns & growth intelligence pipeline",
        "row_counts": {
            "raw_orders": recon["raw_orders"],
            "cleaned_orders": recon["cleaned_orders"],
            "duplicates_removed": recon["duplicates_removed"],
            "customers": 45,
            "products": 16,
        },
        "revenue": {
            "raw_sql_discounted_revenue": recon["raw_revenue"],
            "cleaned_python_revenue": round(recon["cleaned_revenue"], 2),
            "revenue_delta": recon["revenue_delta"],
            "currency": "INR",
            "note": "Revenue = quantity * price * (1 - discount_pct/100); returned orders included.",
        },
        "return_rates_by_payment": {
            method: {
                "returned": int(hyp["rates"]["returned"][method]),
                "total": int(hyp["rates"]["total"][method]),
                "return_rate_pct": float(hyp["rates"]["return_rate"][method]),
            }
            for method in hyp["rates"]["returned"]
        },
        "cod_hypothesis": {
            "h0": "COD orders do not have a higher return rate than non-COD orders",
            "h1": "COD orders have a higher return rate than non-COD orders",
            "cod_rate_pct": hyp["cod_rate_pct"],
            "non_cod_rate_pct": hyp["non_rate_pct"],
            "z_statistic": hyp["z_stat"],
            "p_value": hyp["p_value"],
            "risk_difference_pp": hyp["risk_diff_pp"],
            "verdict": hyp["verdict"],
            "alpha": 0.05,
        },
        "highest_risk_segment": seg["highest_risk"],
        "correlation_summaries": corr["labels"],
        "monthly_revenue": {
            "all_cleaned": trends["all_cleaned"],
            "outlier_excluded": trends["outlier_excluded"],
            "peak_all": {
                "month": trends["peak_all_month"],
                "value": trends["peak_all_value"],
            },
            "peak_corrected": {
                "month": trends["peak_corrected_month"],
                "value": trends["peak_corrected_value"],
            },
        },
        "quantity_outliers": {
            "q1": outlier["q1"],
            "q3": outlier["q3"],
            "iqr": outlier["iqr"],
            "lower_bound": outlier["lower"],
            "upper_bound": outlier["upper"],
            "flagged_order_ids": outlier["flagged_order_ids"],
            "flagged_count": outlier["flagged_count"],
        },
        "data_quality_warnings": [
            "15 ratings were missing and imputed with the median (3.0).",
            "12 discount_pct values were missing and filled with 0.",
            "5 exact duplicate order submissions were removed.",
            "Two quantity outliers (25 and 30) heavily inflate January revenue.",
            "Observational data – statistical associations do not imply causation.",
            "Sample sizes for some payment × city-tier cells are modest (<30).",
        ],
        "limitations": [
            "Dataset is a synthetic/educational sample; not official Mamaearth financials.",
            "No customer lifetime value or repeat-purchase sequence analysis performed.",
            "Return reasons and product quality signals are absent.",
            "Payment-method standardization assumes the seven raw labels map only to UPI/Card/COD.",
        ],
    }
    return findings


def write_findings(results: dict[str, Any], path: Path | None = None) -> Path:
    """Serialize findings to JSON and validate."""
    if path is None:
        path = OUTPUTS_DIR / "findings.json"
    path.parent.mkdir(parents=True, exist_ok=True)

    findings = build_findings(results)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(findings, f, indent=2, ensure_ascii=False)

    # Round-trip validation
    with open(path, encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["row_counts"]["cleaned_orders"] == 175
    assert abs(loaded["revenue"]["cleaned_python_revenue"] - 97358.3) < 0.1
    assert loaded["cod_hypothesis"]["cod_rate_pct"] == 44.4
    print(f"findings.json written and validated → {path}")
    return path


if __name__ == "__main__":
    from src.analysis import run_full_analysis
    res = run_full_analysis()
    write_findings(res)