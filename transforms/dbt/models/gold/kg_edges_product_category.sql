{{ config(materialized='table') }}

select
    p.product_id,
    pc.category_id
from {{ ref('dim_product') }} p
join {{ ref('dim_product_category') }} pc
  on p.product_id = pc.product_id
