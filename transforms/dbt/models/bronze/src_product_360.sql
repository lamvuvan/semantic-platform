{{ config(materialized='view') }}

select
    product_id,
    merchant_id,
    name,
    description,
    base_price,
    status,
    updated_at
from {{ source('product_360', 'products') }}
