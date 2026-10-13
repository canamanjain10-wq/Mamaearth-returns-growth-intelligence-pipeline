-- Mamaearth Analysis Capstone - SQLite Schema
-- Safely rerunnable: drops existing tables first (CASCADE not needed in SQLite)

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS products;

CREATE TABLE customers (
    customer_id   TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    city          TEXT NOT NULL,
    city_tier     INTEGER NOT NULL,
    signup_date   TEXT NOT NULL,          -- ISO date YYYY-MM-DD
    acquisition_source TEXT NOT NULL
);

CREATE TABLE products (
    product_id    TEXT PRIMARY KEY,
    product_name  TEXT NOT NULL,
    category      TEXT NOT NULL,
    price         REAL NOT NULL CHECK (price >= 0)
);

CREATE TABLE orders (
    order_id        TEXT PRIMARY KEY,
    customer_id     TEXT NOT NULL,
    product_id      TEXT NOT NULL,
    order_date      TEXT NOT NULL,        -- ISO date YYYY-MM-DD
    quantity        INTEGER NOT NULL CHECK (quantity > 0),
    discount_pct    REAL,                 -- nullable; treat as 0 when NULL
    payment_method  TEXT NOT NULL,
    rating          REAL,                 -- nullable
    returned        INTEGER NOT NULL DEFAULT 0 CHECK (returned IN (0, 1)),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (product_id)  REFERENCES products(product_id)
);

-- Verify FK enforcement is on
PRAGMA foreign_keys;