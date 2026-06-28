
      
  
    

  create  table "electricity"."silver_silver"."weather_hourly"
  
  
    as
  
  (
    

SELECT
    (raw_payload->>'time')::TIMESTAMPTZ AS time,
    (raw_payload->>'region_id')::VARCHAR(10) AS region_id,
    (raw_payload->>'temperature_2m')::NUMERIC AS temperature_2m,
    (raw_payload->>'relative_humidity_2m')::NUMERIC AS relative_humidity_2m,
    COALESCE((raw_payload->>'precipitation')::NUMERIC, 0) AS precipitation,
    COALESCE((raw_payload->>'cloud_cover')::NUMERIC, 0) AS cloud_cover,
    (raw_payload->>'wind_speed_10m')::NUMERIC AS wind_speed_10m,
    COALESCE((raw_payload->>'shortwave_radiation')::NUMERIC, 0) AS shortwave_radiation,
    NOW() AS updated_at
FROM "electricity"."bronze"."weather"
WHERE raw_payload->>'temperature_2m' IS NOT NULL
  AND raw_payload->>'time' IS NOT NULL
  AND raw_payload->>'region_id' IN ('NSW1', 'QLD1', 'SA1', 'TAS1', 'VIC1')


  );
  
  