{{ config(materialized='table') }}

-- Gold layer: phẳng dữ liệu thành dạng nodes export sang CSV cho Neo4j loader.
select
    product_id,
    merchant_id,
    name,
    name_normalized,
    description,
    base_price,
    status
from {{ ref('dim_product') }}
where status = 'active'
