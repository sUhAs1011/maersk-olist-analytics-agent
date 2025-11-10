# Olist DB Schema

## customers

- `customer_id` (VARCHAR)
- `customer_unique_id` (VARCHAR)
- `customer_zip_code_prefix` (BIGINT)
- `customer_city` (VARCHAR)
- `customer_state` (VARCHAR)

## geolocation

- `geolocation_zip_code_prefix` (BIGINT)
- `geolocation_lat` (DOUBLE)
- `geolocation_lng` (DOUBLE)
- `geolocation_city` (VARCHAR)
- `geolocation_state` (VARCHAR)

## items

- `order_id` (VARCHAR)
- `order_item_id` (BIGINT)
- `product_id` (VARCHAR)
- `seller_id` (VARCHAR)
- `shipping_limit_date` (TIMESTAMP WITH TIME ZONE)
- `price` (DOUBLE) – Item price in BRL
- `freight_value` (DOUBLE) – Shipping (freight) value in BRL

## orders

- `order_id` (VARCHAR)
- `customer_id` (VARCHAR)
- `order_status` (VARCHAR)
- `order_purchase_timestamp` (TIMESTAMP WITH TIME ZONE) – UTC timestamp when order was placed
- `order_approved_at` (TIMESTAMP WITH TIME ZONE)
- `order_delivered_carrier_date` (TIMESTAMP WITH TIME ZONE)
- `order_delivered_customer_date` (TIMESTAMP WITH TIME ZONE) – Actual delivery date to customer
- `order_estimated_delivery_date` (TIMESTAMP WITH TIME ZONE) – Estimated delivery date

## payments

- `order_id` (VARCHAR)
- `payment_sequential` (BIGINT)
- `payment_type` (VARCHAR)
- `payment_installments` (BIGINT)
- `payment_value` (DOUBLE) – Total paid value for the order

## product_category_translation

- `product_category_name` (VARCHAR)
- `product_category_name_english` (VARCHAR) – Category name in English

## products

- `product_id` (VARCHAR)
- `product_category_name` (VARCHAR) – Original Portuguese category name
- `product_name_lenght` (DOUBLE)
- `product_description_lenght` (DOUBLE)
- `product_photos_qty` (DOUBLE)
- `product_weight_g` (DOUBLE)
- `product_length_cm` (DOUBLE)
- `product_height_cm` (DOUBLE)
- `product_width_cm` (DOUBLE)

## reviews

- `review_id` (VARCHAR)
- `order_id` (VARCHAR)
- `review_score` (BIGINT) – Customer review score (1-5)
- `review_comment_title` (VARCHAR)
- `review_comment_message` (VARCHAR)
- `review_creation_date` (TIMESTAMP WITH TIME ZONE)
- `review_answer_timestamp` (TIMESTAMP WITH TIME ZONE)

## sellers

- `seller_id` (VARCHAR)
- `seller_zip_code_prefix` (BIGINT)
- `seller_city` (VARCHAR)
- `seller_state` (VARCHAR)

## v_order_enriched

- `order_id` (VARCHAR)
- `customer_id` (VARCHAR)
- `order_purchase_timestamp` (TIMESTAMP WITH TIME ZONE)
- `order_delivered_customer_date` (TIMESTAMP WITH TIME ZONE)
- `order_estimated_delivery_date` (TIMESTAMP WITH TIME ZONE)
- `delivery_delay_days` (BIGINT)
- `order_revenue` (DOUBLE)

