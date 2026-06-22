{{
  config(
    materialized='incremental',
    unique_key=['time', 'region_id']
  )
}}

WITH demand_hourly AS (
    SELECT
        date_trunc('hour', time) AS time,
        region_id,
        AVG(demand_mw) AS demand_mw
    FROM {{ ref('demand_5min') }}
    GROUP BY date_trunc('hour', time), region_id
),

weather_aligned AS (
    SELECT
        time,
        region_id,
        temperature_2m,
        relative_humidity_2m,
        precipitation,
        cloud_cover,
        wind_speed_10m,
        shortwave_radiation
    FROM {{ ref('weather_hourly') }}
),

{% if is_incremental() %}
latest_ts AS (
    SELECT COALESCE(MAX(time), '1900-01-01') AS max_time FROM {{ this }}
),
{% endif %}

joined AS (
    SELECT
        d.time,
        d.region_id,
        d.demand_mw,
        w.temperature_2m,
        w.relative_humidity_2m,
        w.precipitation,
        w.cloud_cover,
        w.wind_speed_10m,
        w.shortwave_radiation
    FROM demand_hourly d
    LEFT JOIN weather_aligned w ON d.time = w.time AND d.region_id = w.region_id
    {% if is_incremental() %}
      , latest_ts
      WHERE d.time > latest_ts.max_time
    {% endif %}
)

SELECT
    time,
    region_id,
    demand_mw,
    temperature_2m,
    relative_humidity_2m,
    precipitation,
    cloud_cover,
    wind_speed_10m,
    shortwave_radiation,
    EXTRACT(HOUR FROM time)::INT AS hour,
    EXTRACT(DOW FROM time)::INT AS day_of_week,
    (EXTRACT(DOW FROM time) IN (0, 6)) AS is_weekend,
    EXTRACT(MONTH FROM time)::INT AS month,
    CASE
        WHEN EXTRACT(MONTH FROM time) IN (12, 1, 2) THEN 1
        WHEN EXTRACT(MONTH FROM time) IN (3, 4, 5) THEN 2
        WHEN EXTRACT(MONTH FROM time) IN (6, 7, 8) THEN 3
        ELSE 4
    END AS season,
    CASE
        WHEN EXTRACT(MONTH FROM time) IN (12, 1, 2) THEN 'summer'
        WHEN EXTRACT(MONTH FROM time) IN (3, 4, 5) THEN 'autumn'
        WHEN EXTRACT(MONTH FROM time) IN (6, 7, 8) THEN 'winter'
        ELSE 'spring'
    END AS season_name,
    NOW() AS updated_at
FROM joined
WHERE demand_mw IS NOT NULL
