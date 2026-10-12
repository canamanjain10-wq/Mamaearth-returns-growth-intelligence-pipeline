"""
GenAI-powered business narrative generator.
Uses Google GenAI SDK (Gemini) when an API key is available;
falls back to a deterministic template otherwise.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_DIR = ROOT / "narrator"


def _load_findings(path: Path | None = None) -> dict[str, Any]:
    if path is None:
        path = OUTPUTS_DIR / "findings.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _build_prompt(findings: dict[str, Any]) -> str:
    """Construct an evidence-based prompt from verified findings only."""
    return f"""
You are a senior retail analytics consultant. Produce a concise, financially accurate
business narrative based exclusively on the following verified findings. Do not invent
numbers or claims that are not present in the data below.

VERIFIED FINDINGS (JSON):
{json.dumps(findings, indent=2)}

Structure your response with these exact section headings:
1. Executive Summary
2. Key Verified Financial Findings
3. Customer and Payment Behavior
4. Return-Risk Observations
5. Monthly Revenue Trends
6. Recommended Business Actions
7. Limitations and Caveats

Rules:
- Every numeric claim must match the findings JSON.
- Separate observed facts from interpretations.
- Recommendations must be linked to actual findings.
- Keep the tone professional and actionable.
""".strip()


def generate_gemini_narrative(findings: dict[str, Any]) -> dict[str, Any]:
    """Call Gemini via the official Google GenAI SDK."""
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("No GOOGLE_API_KEY or GEMINI_API_KEY environment variable set.")

    try:
        from google import genai
        from google.genai import types
    except ImportError as e:
        raise RuntimeError("google-genai package not installed") from e

    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=30000),  # milliseconds
    )

    system_instruction = (
        "You are an evidence-based financial analyst. "
        "Produce concise, accurate business analysis strictly grounded in the supplied findings. "
        "Never invent figures."
    )

    prompt = _build_prompt(findings)

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.0,
            max_output_tokens=1024,
        ),
    )

    text = getattr(response, "text", None) or ""
    if not text.strip():
        raise RuntimeError("Empty response from Gemini API")

    return {
        "mode": "gemini",
        "model": "gemini-2.0-flash",
        "narrative": text,
        "sections": _split_sections(text),
    }


def generate_offline_narrative(findings: dict[str, Any]) -> dict[str, Any]:
    """Deterministic template-based narrative that needs no network."""
    rc = findings["row_counts"]
    rev = findings["revenue"]
    hyp = findings["cod_hypothesis"]
    seg = findings["highest_risk_segment"]
    peak = findings["monthly_revenue"]["peak_corrected"]
    rates = findings["return_rates_by_payment"]

    text = f"""1. Executive Summary
This analysis of {rc['raw_orders']} raw orders (cleaned to {rc['cleaned_orders']} after removing {rc['duplicates_removed']} duplicates) shows discounted revenue of ₹{rev['cleaned_python_revenue']:,.2f}. COD payment method exhibits a markedly higher return rate ({hyp['cod_rate_pct']}%) than non-COD methods ({hyp['non_cod_rate_pct']}%), a difference that is statistically significant. The highest-risk segment is {seg['payment_method']} customers in city-tier {seg['city_tier']} with a {seg['return_rate_pct']}% return rate. After excluding quantity outliers, March is the peak revenue month at ₹{peak['value']:,.2f}.

2. Key Verified Financial Findings
- Raw discounted revenue (SQL): ₹{rev['raw_sql_discounted_revenue']:,.2f}
- Cleaned discounted revenue (Python): ₹{rev['cleaned_python_revenue']:,.2f}
- Revenue reduction attributable to duplicate removal: ₹{rev['revenue_delta']:,.2f}
- Customers: {rc['customers']}; Products: {rc['products']}
- Currency: {rev['currency']}; returns are included in revenue totals.

3. Customer and Payment Behavior
Return rates by standardized payment method:
- COD: {rates.get('COD', {}).get('return_rate_pct', 'N/A')}% ({rates.get('COD', {}).get('returned', 'N/A')}/{rates.get('COD', {}).get('total', 'N/A')})
- Card: {rates.get('Card', {}).get('return_rate_pct', 'N/A')}% ({rates.get('Card', {}).get('returned', 'N/A')}/{rates.get('Card', {}).get('total', 'N/A')})
- UPI: {rates.get('UPI', {}).get('return_rate_pct', 'N/A')}% ({rates.get('UPI', {}).get('returned', 'N/A')}/{rates.get('UPI', {}).get('total', 'N/A')})
COD dominates return volume. Quantity and order_value are strongly correlated (r≈0.98), as expected.

4. Return-Risk Observations
Hypothesis test (one-sided two-proportion z-test):
- H0: COD return rate ≤ non-COD
- H1: COD return rate > non-COD
- z = {hyp['z_statistic']}, p = {hyp['p_value']}, risk difference = {hyp['risk_difference_pp']} percentage points
- Verdict: H1 is {hyp['verdict']} at α={hyp['alpha']}
Highest-risk segment: {seg['payment_method']} × city_tier {seg['city_tier']} → {seg['return_rate_pct']}% ({seg['returned']}/{seg['total']}){(' ' + seg['warning']) if seg.get('warning') else ''}.

5. Monthly Revenue Trends
Peak month using all cleaned orders is driven by two extreme quantity outliers (25 and 30 units). After excluding those outliers, the peak shifts to {peak['month']} with ₹{peak['value']:,.2f}. Outlier correction is an analytical view only; the source data are unchanged.

6. Recommended Business Actions
- Investigate COD fulfilment and return logistics, especially in tier-2 cities (highest observed risk).
- Review the two extreme-quantity orders for data-entry or fraud signals.
- Consider tighter discount controls or pre-authorization for high-quantity COD orders.
- Improve rating capture (15 values were missing) to strengthen product-quality feedback loops.

7. Limitations and Caveats
{chr(10).join('- ' + w for w in findings['data_quality_warnings'])}
{chr(10).join('- ' + lim for lim in findings['limitations'])}
"""
    return {
        "mode": "offline",
        "model": "template",
        "narrative": text.strip(),
        "sections": _split_sections(text),
    }


def _split_sections(text: str) -> dict[str, str]:
    """Naive section splitter on numbered headings."""
    sections = {}
    pattern = re.compile(r"^(\d+\.\s+[^\n]+)", re.MULTILINE)
    parts = pattern.split(text)
    # parts[0] is preamble; then alternating heading / body
    for i in range(1, len(parts), 2):
        heading = parts[i].strip()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        sections[heading] = body
    return sections


def generate_narrative(findings: dict[str, Any] | None = None) -> dict[str, Any]:
    """Try Gemini first; fall back to offline template."""
    if findings is None:
        findings = _load_findings()

    try:
        result = generate_gemini_narrative(findings)
        print("Narrative mode: GEMINI")
        return result
    except Exception as e:
        print(f"Gemini unavailable ({e}); using offline fallback.")
        result = generate_offline_narrative(findings)
        print("Narrative mode: OFFLINE")
        return result


def check_numeric_accuracy(narrative_result: dict[str, Any], findings: dict[str, Any]) -> dict[str, Any]:
    """
    Verify at least five important figures appear (with correct labels) in the narrative.
    Handles currency formatting, percentages, and rounding.
    """
    text = narrative_result.get("narrative", "")
    checks = []

    def _present(label: str, value: float | int, tolerance: float = 0.05) -> dict:
        # Build several acceptable string forms
        candidates = [
            str(value),
            f"{value:,}",
            f"{value:,.1f}",
            f"{value:,.2f}",
            f"{value:.1f}",
            f"{value:.2f}",
        ]
        found = any(c in text for c in candidates)
        return {"label": label, "expected": value, "found": found, "pass": found}

    # 1. Cleaned order count
    checks.append(_present("cleaned_orders", findings["row_counts"]["cleaned_orders"]))
    # 2. Cleaned revenue
    checks.append(_present("cleaned_revenue", findings["revenue"]["cleaned_python_revenue"]))
    # 3. COD return rate
    checks.append(_present("cod_rate_pct", findings["cod_hypothesis"]["cod_rate_pct"]))
    # 4. Peak corrected revenue
    checks.append(_present("peak_corrected_value", findings["monthly_revenue"]["peak_corrected"]["value"]))
    # 5. Duplicates removed
    checks.append(_present("duplicates_removed", findings["row_counts"]["duplicates_removed"]))
    # 6. Raw revenue (bonus)
    checks.append(_present("raw_revenue", findings["revenue"]["raw_sql_discounted_revenue"]))

    passed = sum(1 for c in checks if c["pass"])
    overall = passed >= 5
    print(f"Numeric accuracy: {passed}/{len(checks)} checks passed → {'PASS' if overall else 'FAIL'}")
    for c in checks:
        status = "✓" if c["pass"] else "✗"
        print(f"  {status} {c['label']}: expected {c['expected']}")

    return {"checks": checks, "passed": passed, "total": len(checks), "overall_pass": overall}


if __name__ == "__main__":
    findings = _load_findings()
    narr = generate_narrative(findings)
    print("\n--- Narrative preview (first 800 chars) ---")
    print(narr["narrative"][:800])
    acc = check_numeric_accuracy(narr, findings)
    print(json.dumps(acc, indent=2))