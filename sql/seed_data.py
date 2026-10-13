#!/usr/bin/env python3
"""
Load the three CSV files into SQLite.
Rerunnable: schema is recreated; tables are emptied before insert.
Blank cells become SQL NULL.
"""

import csv
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "mamaearth.db"
DATA_DIR = ROOT / "data"
SCHEMA_PATH = ROOT / "sql" / "schema.sql"


def load_csv_to_table(conn: sqlite3.Connection, csv_path: Path, table: str, columns: list[str]) -> int:
    """Insert CSV rows into table. Returns number of rows inserted."""
    cur = conn.cursor()
    placeholders = ",".join("?" * len(columns))
    col_list = ",".join(columns)
    sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"

    inserted = 0
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            values = []
            for col in columns:
                val = row.get(col, "")
                if val is None or (isinstance(val, str) and val.strip() == ""):
                    values.append(None)
                else:
                    values.append(val)
            cur.execute(sql, values)
            inserted += 1
    return inserted


def main() -> None:
    print("=" * 60)
    print("Mamaearth SQLite Seed Loader")
    print("=" * 60)
    print(f"Database : {DB_PATH}")
    print(f"Data dir : {DATA_DIR}")

    # Recreate schema (drops + creates)
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        schema_sql = f.read()

    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(schema_sql)
    print("Schema applied (tables recreated).")

    # Load data
    cust_cols = ["customer_id", "name", "city", "city_tier", "signup_date", "acquisition_source"]
    prod_cols = ["product_id", "product_name", "category", "price"]
    ord_cols  = ["order_id", "customer_id", "product_id", "order_date", "quantity",
                 "discount_pct", "payment_method", "rating", "returned"]

    n_cust = load_csv_to_table(conn, DATA_DIR / "customers.csv", "customers", cust_cols)
    n_prod = load_csv_to_table(conn, DATA_DIR / "products.csv",  "products",  prod_cols)
    n_ord  = load_csv_to_table(conn, DATA_DIR / "orders.csv",    "orders",    ord_cols)

    conn.commit()

    # Verify counts
    cur = conn.cursor()
    counts = {
        "customers": cur.execute("SELECT COUNT(*) FROM customers").fetchone()[0],
        "products":  cur.execute("SELECT COUNT(*) FROM products").fetchone()[0],
        "orders":    cur.execute("SELECT COUNT(*) FROM orders").fetchone()[0],
    }
    print(f"\nInserted rows → customers: {n_cust}, products: {n_prod}, orders: {n_ord}")
    print(f"Table counts  → customers: {counts['customers']}, products: {counts['products']}, orders: {counts['orders']}")

    expected = {"customers": 45, "products": 16, "orders": 180}
    ok = True
    for table, exp in expected.items():
        if counts[table] != exp:
            print(f"ERROR: {table} expected {exp}, got {counts[table]}")
            ok = False
        else:
            print(f"OK: {table} = {exp}")

    # FK integrity checks
    orphan_cust = cur.execute("""
        SELECT COUNT(*) FROM orders o
        LEFT JOIN customers c ON o.customer_id = c.customer_id
        WHERE c.customer_id IS NULL
    """).fetchone()[0]
    orphan_prod = cur.execute("""
        SELECT COUNT(*) FROM orders o
        LEFT JOIN products p ON o.product_id = p.product_id
        WHERE p.product_id IS NULL
    """).fetchone()[0]

    print(f"\nFK check – orders with missing customer: {orphan_cust}")
    print(f"FK check – orders with missing product : {orphan_prod}")
    if orphan_cust or orphan_prod:
        print("ERROR: Foreign-key integrity failed.")
        ok = False
    else:
        print("OK: Foreign-key integrity passed.")

    # Sample NULL handling for discount_pct / rating
    null_disc = cur.execute("SELECT COUNT(*) FROM orders WHERE discount_pct IS NULL").fetchone()[0]
    null_rat  = cur.execute("SELECT COUNT(*) FROM orders WHERE rating IS NULL").fetchone()[0]
    print(f"\nNULL discount_pct rows: {null_disc}")
    print(f"NULL rating rows      : {null_rat}")

    conn.close()
    if not ok:
        sys.exit(1)
    print("\nSeed completed successfully.")


if __name__ == "__main__":
    main()