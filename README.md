Mamaearth Returns & Growth Intelligence Pipeline
Capstone Project — Data Analytics with AI & GenAI Program: E&ICT Academy, IIT Roorkee Developer: Naman Jain
A complete, reproducible data-analytics capstone that follows a clear workflow:
SQL → Data → Analysis (clean & EDA) → Visualizations → Narrator
It combines SQL financial reporting, Python/pandas cleaning & EDA, statistical hypothesis testing, visualization, and a GenAI-powered business narrative (with offline fallback).
Repository Structure 
```
mamaearth-repo/
├── README.md
├── requirements.txt
├── .gitignore
├── .env.example
├── sql/
│   ├── schema.sql          # relational schema (PKs, FKs)
│   ├── seed_data.py        # load CSVs → SQLite
│   ├── reports.sql         # nine business reports
│   ├── run_reports.py      # execute reports, write results
│   └── sql_results/        # saved report outputs
├── data/
│   ├── customers.csv
│   ├── products.csv
│   └── orders.csv
├── analysis/
│   ├── clean_and_eda.py    # load → clean → EDA → stats
│   ├── visualize.py        # charts from cleaned results
│   ├── build_findings.py   # structured findings.json
│   └── validate.py
├── visualizations/
│   ├── return_rate_by_payment.png
│   └── monthly_revenue_comparison.png
└── narrator/
    ├── findings.json
    ├── generate_narrative.py
    └── sample_output.txt
```
---
1. Business Problem & Objectives
E-commerce brands face elevated return rates, especially on Cash-on-Delivery (COD) orders. This project answers:
What is the true discounted revenue after data-quality corrections?
Do COD orders exhibit a statistically higher return rate?
Which payment × city-tier segments carry the highest return risk?
How do extreme quantity outliers distort monthly revenue trends?
Objectives
Build a clean, relational SQLite layer and nine business reports.
Perform transparent pandas cleaning (standardisation, deduplication, imputation).
Reconcile SQL vs Python revenue figures to the rupee.
Test the COD-return hypothesis and segment risk.
Produce publication-ready charts and an evidence-based narrative (Gemini or offline).
---
2. Research Questions
#	Research Question	Method
RQ1	What is the impact of duplicate removal on revenue?	SQL vs Python reconciliation
RQ2	Is the COD return rate higher than non-COD?	One-sided two-proportion z-test
RQ3	Which payment × city-tier cell is highest risk?	Grouped return-rate table
RQ4	How do quantity outliers affect the monthly revenue peak?	IQR flagging + dual trend series
---
3. Technology Stack
Layer	Tools
Database	SQLite 3
Data wrangling	Python 3.10+, pandas, NumPy
Statistics	SciPy
Visualisation	Matplotlib
GenAI	Google GenAI SDK (Gemini)
Testing / validation	pytest (optional)
---
4. Dataset Description
Three CSV files under `data/`:
File	Rows	Key Columns
`customers.csv`	45	customer_id (PK), name, city, city_tier, signup_date, acquisition_source
`products.csv`	16	product_id (PK), product_name, category, price
`orders.csv`	180	order_id (PK), customer_id (FK), product_id (FK), order_date, quantity, discount_pct, payment_method, rating, returned
Relationships  
`orders.customer_id → customers.customer_id`  
`orders.product_id → products.product_id`
---
5. How to Run (chronological order)
Setup
```bash
cd mamaearth-repo
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # optional: add GOOGLE_API_KEY for Gemini
```
Step 1 – SQL layer
```bash
python sql/seed_data.py     # create mamaearth.db and load CSVs
python sql/run_reports.py   # run nine reports → sql/sql_results/
```
Step 2 – Analysis (clean & EDA)
```bash
python analysis/clean_and_eda.py
```
Step 3 – Visualizations
```bash
python analysis/visualize.py
# writes the two PNGs under visualizations/
```
Step 4 – Findings + Narrative
```bash
# After analysis has been run (or use existing findings.json):
python narrator/generate_narrative.py
```
Findings are already present in `narrator/findings.json`.  
`narrator/sample_output.txt` shows a sample narrative (Gemini or offline).
---
6. SQL Layer Summary
schema.sql – PKs/FKs, nullable discount_pct & rating, safely rerunnable.
seed_data.py – blank CSV cells → SQL NULL; verified counts 45 / 16 / 180.
reports.sql – nine business reports (order totals, ratings, high-return cities, top spenders, category revenue, loyalty tiers, etc.).
Key headline figures (after loading):
Metric	Value
Raw orders	180
Discounted revenue (SQL)	₹99,860.20
AOV	₹554.78
---
7. Python Cleaning & EDA (analysis/clean_and_eda.py)
Executed in order:
Load & inspect shapes, dtypes, missingness.
Standardise payment methods → {UPI, Card, COD}.
Remove duplicates on natural key → 175 retained (5 dropped).
Impute `discount_pct` ← 0; `rating` ← median (3.0).
Merge & reconcile order_value = qty × price × (1 − discount/100).
IQR outliers on quantity (flag only; never delete).
COD hypothesis – one-sided two-proportion z-test.
Payment × city-tier segmentation.
Correlation matrix.
Dual monthly revenue series (all cleaned vs outlier-excluded).
---
8. Financial Reconciliation
Metric	Value
Raw SQL discounted revenue	₹99,860.20
Cleaned Python revenue	₹97,358.30
Delta	₹2,501.90
Explanation	Exactly the 5 duplicate order rows removed
Returned orders are included in both revenue figures (gross discounted revenue).
---
9. Visualizations
Produced by `analysis/visualize.py` into `visualizations/`:
return_rate_by_payment.png – return rate (%) by UPI / Card / COD.
monthly_revenue_comparison.png – monthly revenue: all cleaned vs outlier-excluded.
---
10. Narrator
`findings.json` – structured, evidence-only findings from the analysis.
`generate_narrative.py` – Gemini when `GOOGLE_API_KEY` is set; otherwise deterministic offline template.
`sample_output.txt` – example narrative output.
---
11. Key Results (preview)
COD return rate is higher than non-COD (one-sided z-test; see findings for p-value).
Highest-risk payment × city-tier cells are surfaced in the segmentation table.
Quantity outliers (IQR) shift the monthly revenue peak when excluded.
Revenue delta of ₹2,501.90 is fully explained by the five removed duplicates.
Full numbers live in `narrator/findings.json` and the SQL report files.
---
12. Limitations & Future Work
Synthetic educational data – not official company financials.
No return-reason or product-quality signals.
Modest sample sizes in some segments.
Possible extensions: customer LTV, time-to-return survival analysis, COD pre-authorisation A/B simulation.
---
**Disclaimer**  
This project analyses a supplied synthetic order-level dataset for educational and portfolio purposes. It is **not** affiliated with Mamaearth, nor does it represent Mamaearth’s audited corporate financial statements.
MIT License – free for educational and portfolio use.  
Data: supplied CSV files for the capstone exercise; no external proprietary data is redistributed.
Developer: Naman Jain
Program: Data Analytics with AI & GenAI Institution: E&ICT Academy, IIT Roorkee
