# Ingestion & Sanity Report

## Row counts

|    | table                        |   rows |
|----|------------------------------|--------|
|  0 | customers                    |  99441 |
|  1 | geolocation                  | 738332 |
|  2 | items                        | 112650 |
|  3 | orders                       |  99441 |
|  4 | payments                     | 103886 |
|  5 | product_category_translation |     71 |
|  6 | products                     |  32951 |
|  7 | reviews                      |  99224 |
|  8 | sellers                      |   3095 |

## Key column null rates

|    | table     | column       |   total_rows |   null_rows |   null_pct |
|----|-----------|--------------|--------------|-------------|------------|
|  0 | orders    | order_id     |        99441 |           0 |          0 |
|  1 | orders    | customer_id  |        99441 |           0 |          0 |
|  2 | items     | order_id     |       112650 |           0 |          0 |
|  3 | items     | product_id   |       112650 |           0 |          0 |
|  4 | payments  | order_id     |       103886 |           0 |          0 |
|  5 | reviews   | order_id     |        99224 |           0 |          0 |
|  6 | reviews   | review_score |        99224 |           0 |          0 |
|  7 | customers | customer_id  |        99441 |           0 |          0 |
|  8 | products  | product_id   |        32951 |           0 |          0 |
|  9 | sellers   | seller_id    |         3095 |           0 |          0 |

## Referential integrity (violations)

|    | check            | child_table   | child_key   | parent_table   | parent_key   |   violations |
|----|------------------|---------------|-------------|----------------|--------------|--------------|
|  0 | items→orders     | items         | order_id    | orders         | order_id     |            0 |
|  1 | items→products   | items         | product_id  | products       | product_id   |            0 |
|  2 | orders→customers | orders        | customer_id | customers      | customer_id  |            0 |
|  3 | payments→orders  | payments      | order_id    | orders         | order_id     |            0 |
|  4 | reviews→orders   | reviews       | order_id    | orders         | order_id     |            0 |
