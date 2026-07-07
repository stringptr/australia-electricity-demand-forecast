{{
  config(
    materialized='incremental',
    unique_key=['time', 'region_id'],
    pre_hook="{% if is_incremental() %}ALTER TABLE {{ this }} REPLICA IDENTITY FULL{% else %}SELECT 1{% endif %}"
  )
}}

{% if is_incremental() %}
WITH region_latest AS (
    SELECT region_id, MAX(time) AS max_time
    FROM {{ this }}
    GROUP BY region_id
)
{% endif %}

SELECT
    d.time,
    d.region_id,
    d.demand_mw,
    NOW() AS updated_at
FROM {{ source('bronze', 'demand') }} d
{% if is_incremental() %}
LEFT JOIN region_latest rl ON d.region_id = rl.region_id
{% endif %}
WHERE d.demand_mw IS NOT NULL
  AND d.time IS NOT NULL
  AND d.region_id IN ('NSW1', 'QLD1', 'SA1', 'TAS1', 'VIC1')
  {% if is_incremental() %}
  AND (rl.max_time IS NULL OR d.time > rl.max_time)
  {% endif %}
