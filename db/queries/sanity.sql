-- Row counts
SELECT 'customers' AS table_name, COUNT(*) AS rows FROM customers
UNION ALL SELECT 'geolocation', COUNT(*) FROM geolocation
UNION ALL SELECT 'items', COUNT(*) FROM items
UNION ALL SELECT 'payments', COUNT(*) FROM payments
UNION ALL SELECT 'reviews', COUNT(*) FROM reviews
UNION ALL SELECT 'orders', COUNT(*) FROM orders
UNION ALL SELECT 'products', COUNT(*) FROM products
UNION ALL SELECT 'sellers', COUNT(*) FROM sellers
UNION ALL SELECT 'product_category_translation', COUNT(*) FROM product_category_translation
ORDER BY table_name;

-- Basic null rates for key columns
WITH cols AS (
  SELECT 'orders' AS t, 'order_id' AS c UNION ALL
  SELECT 'orders','customer_id' UNION ALL
  SELECT 'items','order_id' UNION ALL
  SELECT 'items','product_id' UNION ALL
  SELECT 'payments','order_id' UNION ALL
  SELECT 'reviews','order_id' UNION ALL
  SELECT 'products','product_id' UNION ALL
  SELECT 'customers','customer_id' UNION ALL
  SELECT 'sellers','seller_id'
),
counts AS (
  SELECT t, c,
         (SELECT COUNT(*) FROM duckdb_tables() WHERE table_name=t) AS _dummy -- just to keep structure
  FROM cols
)
SELECT
  c.t AS table_name,
  c.c AS column_name,
  (SELECT COUNT(*) FROM (SELECT * FROM (SELECT * FROM (SELECT * FROM (SELECT * FROM (SELECT * FROM (SELECT * FROM (SELECT * FROM (SELECT 1) x)))))))) AS total_rows, -- placeholder; we'll compute in Python
  NULL AS null_rows
FROM cols c;
