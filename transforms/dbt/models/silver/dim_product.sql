{{ config(materialized='incremental', unique_key='product_id') }}

with src as (
    select * from {{ ref('src_product_360') }}
    {% if is_incremental() %}
    where updated_at > (select coalesce(max(updated_at), '1900-01-01') from {{ this }})
    {% endif %}
)

select
    product_id,
    merchant_id,
    name,
    lower(regexp_replace(name, '[^[:alnum:][:space:]]', '')) as name_normalized,
    description,
    base_price,
    status,
    updated_at
from src
