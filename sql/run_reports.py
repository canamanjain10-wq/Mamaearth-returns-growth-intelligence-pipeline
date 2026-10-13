#!/usr/bin/env python3
"""Execute reports.sql and save each result set to outputs/sql_results/."""

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "mamaearth.db"
REPORTS_SQL = ROOT / "sql" / "reports.sql"
OUT_DIR = ROOT / "sql" / "sql_results"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Ensure loyalty_tier exists (report 9)
    try:
        cols = [r[1] for r in cur.execute("PRAGMA table_info(customers)")]
        if "loyalty_tier" not in cols:
            cur.execute("ALTER TABLE customers ADD COLUMN loyalty_tier TEXT")
            conn.commit()
            print("Added loyalty_tier column")
        else:
            print("loyalty_tier column already present")
    except Exception as e:
        print(f"Note: could not alter table ({e}); continuing")

    sql_text = REPORTS_SQL.read_text(encoding="utf-8")
    # Split on statement boundaries (simple approach: split by semicolon after comments)
    statements = []
    current = []
    for line in sql_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue  # skip pure comment lines for execution
        current.append(line)
        if stripped.endswith(";"):
            stmt = "\n".join(current).strip()
            if stmt and not stmt.startswith("--"):
                statements.append(stmt)
            current = []

    print(f"Found {len(statements)} executable statements")
    for i, stmt in enumerate(statements, 1):
        print(f"\n--- Statement {i} ---")
        try:
            cur.execute(stmt)
            if cur.description:
                rows = cur.fetchall()
                cols = [d[0] for d in cur.description]
                print(" | ".join(cols))
                for r in rows:
                    print(" | ".join(str(r[c]) for c in cols))
                # Save to file
                out_file = OUT_DIR / f"report_{i:02d}.txt"
                with open(out_file, "w", encoding="utf-8") as f:
                    f.write(" | ".join(cols) + "\n")
                    for r in rows:
                        f.write(" | ".join(str(r[c]) for c in cols) + "\n")
                print(f"Saved → {out_file}")
            else:
                print(f"(no result set, rowcount={cur.rowcount})")
                conn.commit()
        except Exception as e:
            print(f"ERROR: {e}")
            print(stmt[:200])

    conn.close()
    print("\nAll reports executed.")


if __name__ == "__main__":
    main()