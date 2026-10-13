-- Mamaearth Analysis Capstone - Nine Business Reports
-- Each query is preceded by its exact verified output (captured from SQLite).
-- Revenue definition: quantity * price * (1 - COALESCE(discount_pct,0)/100.0)
-- Returned orders are included in revenue totals (gross discounted revenue).
-- Run after load_seed.py has populated mamaearth.db

PRAGMA foreign_keys = ON;

-- =============================================================================
-- 1. Order totals
-- Business purpose: Overall order volume, gross & discounted revenue, AOV.
-- Verified output:
--   total_orders | gross_revenue | discounted_revenue | avg_order_value
--   180          | 116840.0      | 99860.2            | 554.78
-- =============================================================================
SELECT
    COUNT(*) AS total_orders,
    ROUND(SUM(o.quantity * p.price), 2) AS gross_revenue,
    ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2) AS discounted_revenue,
    ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)) / COUNT(*), 2) AS avg_order_value
FROM orders o
JOIN products p ON o.product_id = p.product_id;

-- =============================================================================
-- 2. COUNT(*) vs COUNT(rating)
-- Business purpose: Quantify rating completeness for data-quality assessment.
-- Verified output:
--   total_orders | orders_with_rating
--   180          | 165
-- =============================================================================
SELECT COUNT(*) AS total_orders, COUNT(rating) AS orders_with_rating
FROM orders;

-- =============================================================================
-- 3. Customers with zero orders (LEFT JOIN and NOT IN)
-- Business purpose: Identify never-purchased customers for acquisition follow-up.
-- Verified output (both methods identical):
--   customer_id | name
--   C045        | Vihaan
-- =============================================================================
SELECT c.customer_id, c.name
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
WHERE o.order_id IS NULL
ORDER BY c.customer_id;

SELECT customer_id, name
FROM customers
WHERE customer_id NOT IN (SELECT customer_id FROM orders WHERE customer_id IS NOT NULL)
ORDER BY customer_id;

-- =============================================================================
-- 4. GROUP BY + HAVING: return rate by city > 20%
-- Business purpose: Flag high-return cities for operational review.
-- Verified output:
--   city      | total_orders | returned_orders | return_rate_pct
--   Jaipur    | 19           | 8               | 42.11
--   Lucknow   | 49           | 15              | 30.61
--   Bangalore | 33           | 8               | 24.24
-- =============================================================================
SELECT c.city,
       COUNT(*) AS total_orders,
       SUM(o.returned) AS returned_orders,
       ROUND(100.0 * SUM(o.returned) / COUNT(*), 2) AS return_rate_pct
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
GROUP BY c.city
HAVING ROUND(100.0 * SUM(o.returned) / COUNT(*), 2) > 20
ORDER BY return_rate_pct DESC;

-- =============================================================================
-- 5. Top-5 customers by spend; then ranks 3-5 via OFFSET
-- Business purpose: Identify high-value customers; demonstrate pagination.
-- Ties handled by stable ORDER BY total_spend DESC (no secondary key).
-- Verified top-5:
--   C043 Reyansh 12920.0
--   C026 Isha     8371.6
--   C008 Meera    4564.6
--   C011 Arjun    4111.0
--   C042 Sanya    3785.0
-- Ranks 3-5 (OFFSET 2 LIMIT 3): Meera, Arjun, Sanya
-- =============================================================================
SELECT c.customer_id, c.name,
       ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2) AS total_spend
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
JOIN products p ON o.product_id = p.product_id
GROUP BY c.customer_id, c.name
ORDER BY total_spend DESC
LIMIT 5;

SELECT c.customer_id, c.name,
       ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2) AS total_spend
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
JOIN products p ON o.product_id = p.product_id
GROUP BY c.customer_id, c.name
ORDER BY total_spend DESC
LIMIT 3 OFFSET 2;

-- =============================================================================
-- 6. Three-table JOIN: order count & revenue by product category
-- Business purpose: Category contribution to volume and revenue.
-- Verified output:
--   Haircare     54 orders  44956.1
--   Skincare     60 orders  27346.0
--   Babycare     30 orders  16805.0
--   PersonalCare 36 orders  10753.1
-- =============================================================================
SELECT p.category,
       COUNT(*) AS order_count,
       ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2) AS revenue
FROM orders o
JOIN products p ON o.product_id = p.product_id
GROUP BY p.category
ORDER BY revenue DESC;

-- =============================================================================
-- 7. LIKE: customers whose names start with A
-- Business purpose: Simple name-pattern filter for CRM segments.
-- Verified output (10 rows): Aarav, Aditi, Aditya, Aisha, Ananya, Anika, Aria, Arjun, Aryan, Ayaan
-- =============================================================================
SELECT customer_id, name, city
FROM customers
WHERE name LIKE 'A%'
ORDER BY name;

-- =============================================================================
-- 8. DISTINCT: customer acquisition sources
-- Business purpose: Inventory of marketing channels present in the data.
-- Verified output: Ad, Organic, Referral, Social
-- =============================================================================
SELECT DISTINCT acquisition_source
FROM customers
ORDER BY acquisition_source;

-- =============================================================================
-- 9. ALTER + UPDATE CASE: add loyalty_tier (Gold for city_tier=1, else Silver)
-- Business purpose: Simple tiering for loyalty program prototyping.
-- Rerunnable: column added only if missing; UPDATE always applied.
-- Verified distribution after update: Gold 28, Silver 17
-- =============================================================================
-- Note: SQLite has no IF NOT EXISTS for columns; application code should
-- guard the ALTER. For pure SQL reruns, the following is safe once column exists.
-- ALTER TABLE customers ADD COLUMN loyalty_tier TEXT;  -- run once

UPDATE customers
SET loyalty_tier = CASE
    WHEN city_tier = 1 THEN 'Gold'
    ELSE 'Silver'
END;

SELECT loyalty_tier, COUNT(*) AS cnt
FROM customers
GROUP BY loyalty_tier
ORDER BY loyalty_tier;