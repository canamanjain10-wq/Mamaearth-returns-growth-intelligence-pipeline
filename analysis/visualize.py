"""
Visualization step for the Mamaearth pipeline.
Chronological step: analysis/visualize.py
Expects cleaned data / trends from clean_and_eda (or re-runs the pipeline).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
VIS_DIR = ROOT / "visualizations"

# Import cleaning pipeline so this script can stand alone
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from clean_and_eda import run_clean_and_eda

def create_visualizations(df: pd.DataFrame, hyp: dict, trends: dict) -> list[str]:
    """Generate the two required charts and save under visualizations/."""
    print("\n" + "=" * 60)
    print("TASK 11 – Visualizations")
    print("=" * 60)

    VIS_DIR.mkdir(parents=True, exist_ok=True)
    paths = []

    # 1. Return rate by payment method
    rates = (
        df.groupby("payment_method")
        .agg(returned=("returned", "sum"), total=("returned", "count"))
        .assign(rate=lambda x: x["returned"] / x["total"] * 100)
    )
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(rates.index, rates["rate"], color=["#e74c3c", "#3498db", "#2ecc71"])
    ax.set_ylabel("Return Rate (%)")
    ax.set_xlabel("Payment Method")
    ax.set_title("Return Rate by Payment Method")
    ax.set_ylim(0, max(rates["rate"]) * 1.25)
    for bar, rate in zip(bars, rates["rate"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                f"{rate:.1f}%", ha="center", va="bottom", fontsize=11)
    fig.tight_layout()
    p1 = VIS_DIR / "return_rate_by_payment.png"
    fig.savefig(p1, dpi=120)
    plt.close(fig)
    paths.append(str(p1))
    print(f"Saved {p1}")

    # 2. Monthly revenue comparison
    months = sorted(trends["all_cleaned"].keys())
    all_vals = [trends["all_cleaned"][m] for m in months]
    corr_vals = [trends["outlier_excluded"][m] for m in months]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(months, all_vals, marker="o", label="All cleaned orders", linewidth=2)
    ax.plot(months, corr_vals, marker="s", label="Excluding qty outliers", linewidth=2)
    ax.set_xlabel("Month")
    ax.set_ylabel("Revenue (₹)")
    ax.set_title("Monthly Revenue: Cleaned vs Outlier-Excluded")
    ax.legend()
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"Rs.{x:,.0f}"))
    fig.autofmt_xdate()
    fig.tight_layout()
    p2 = VIS_DIR / "monthly_revenue_comparison.png"
    fig.savefig(p2, dpi=120)
    plt.close(fig)
    paths.append(str(p2))
    print(f"Saved {p2}")

    return paths


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def run_visualize() -> list[str]:
    """Run full clean pipeline then produce charts."""
    results = run_clean_and_eda()
    paths = create_visualizations(
        results["merged_df"],
        results["hypothesis"],
        results["trends"],
    )
    return paths


if __name__ == "__main__":
    run_visualize()
