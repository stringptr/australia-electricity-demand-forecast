{{
  config(
    materialized='incremental',
    unique_key=['time', 'region_id']
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
    w.time::TIMESTAMPTZ AS time,
    w.region_id::VARCHAR(10) AS region_id,
    w.temperature_2m::NUMERIC AS temperature_2m,
    w.relative_humidity_2m::NUMERIC AS relative_humidity_2m,
    COALESCE(w.precipitation::NUMERIC, 0) AS precipitation,
    COALESCE(w.cloud_cover::NUMERIC, 0) AS cloud_cover,
    w.wind_speed_10m::NUMERIC AS wind_speed_10m,
    COALESCE(w.shortwave_radiation::NUMERIC, 0) AS shortwave_radiation,
    NOW() AS updated_at
FROM {{ source('bronze', 'weather') }} w
{% if is_incremental() %}
LEFT JOIN region_latest rl ON w.region_id = rl.region_id
{% endif %}
WHERE w.temperature_2m IS NOT NULL
  AND w.time IS NOT NULL
  AND w.region_id IN ('NSW1', 'QLD1', 'SA1', 'TAS1', 'VIC1')
  {% if is_incremental() %}
  AND (rl.max_time IS NULL OR w.time::TIMESTAMPTZ > rl.max_time)
  {% endif %}
