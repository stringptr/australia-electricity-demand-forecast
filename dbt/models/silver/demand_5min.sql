{{
  config(
    materialized='incremental',
    unique_key=['time', 'region_id'],
    pre_hook="{% if is_incremental() %}ALTER TABLE {{ this }} REPLICA IDENTITY FULL{% else %}SELECT 1{% endif %}"
  )
}}

SELECT
    time,
    region_id,
    demand_mw,
    NOW() AS updated_at
FROM {{ source('bronze', 'demand') }}
WHERE demand_mw IS NOT NULL
  AND time IS NOT NULL
  AND region_id IN ('NSW1', 'QLD1', 'SA1', 'TAS1', 'VIC1')

{% if is_incremental() %}
  AND time > (SELECT COALESCE(MAX(time), '1900-01-01') FROM {{ this }})
{% endif %}
