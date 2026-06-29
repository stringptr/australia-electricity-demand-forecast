{{
  config(
    materialized='incremental',
    unique_key=['time', 'region_id']
  )
}}

SELECT
    time::TIMESTAMPTZ AS time,
    region_id::VARCHAR(10) AS region_id,
    temperature_2m::NUMERIC AS temperature_2m,
    relative_humidity_2m::NUMERIC AS relative_humidity_2m,
    COALESCE(precipitation::NUMERIC, 0) AS precipitation,
    COALESCE(cloud_cover::NUMERIC, 0) AS cloud_cover,
    wind_speed_10m::NUMERIC AS wind_speed_10m,
    COALESCE(shortwave_radiation::NUMERIC, 0) AS shortwave_radiation,
    NOW() AS updated_at
FROM {{ source('bronze', 'weather') }}
WHERE temperature_2m IS NOT NULL
  AND time IS NOT NULL
  AND region_id IN ('NSW1', 'QLD1', 'SA1', 'TAS1', 'VIC1')

{% if is_incremental() %}
  AND time::TIMESTAMPTZ > (SELECT COALESCE(MAX(time), '1900-01-01') FROM {{ this }})
{% endif %}
