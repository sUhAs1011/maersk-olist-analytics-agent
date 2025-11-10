-- Order-level revenue (price + freight) and simple delivery delay in days
CREATE OR REPLACE VIEW v_order_enriched AS
SELECT
  o.order_id,
  o.customer_id,
  o.order_purchase_timestamp,
  o.order_delivered_customer_date,
  o.order_estimated_delivery_date,
  DATE_DIFF('day', o.order_estimated_delivery_date, o.order_delivered_customer_date) AS delivery_delay_days,
  SUM(i.price + i.freight_value) AS order_revenue
FROM orders o
LEFT JOIN items i ON i.order_id = o.order_id
GROUP BY 1,2,3,4,5;

-- Customer + geolocation join via zip prefix (best-effort)
CREATE OR REPLACE VIEW v_customer_geo AS
SELECT
  c.customer_id,
  c.customer_unique_id,
  c.customer_city,
  c.customer_state,
  g.geolocation_lat,
  g.geolocation_lng,
  c.geolocation_zip_code_prefix
FROM customers c
LEFT JOIN (
  SELECT geolocation_zip_code_prefix, AVG(geolocation_lat) AS geolocation_lat, AVG(geolocation_lng) AS geolocation_lng
  FROM geolocation
  GROUP BY 1
) g
ON g.geolocation_zip_code_prefix = c.customer_zip_code_prefix;
