{{
  config(
    materialized='incremental',
    unique_key=['time', 'region_id']
  )
}}

SELECT
    (raw_payload->>'SETTLEMENTDATE')::TIMESTAMPTZ AS time,
    (raw_payload->>'REGIONID')::VARCHAR(10) AS region_id,
    (raw_payload->>'TOTALDEMAND')::NUMERIC AS demand_mw,
    NOW() AS updated_at
FROM {{ source('bronze', 'demand') }}
WHERE raw_payload->>'TOTALDEMAND' IS NOT NULL
  AND raw_payload->>'SETTLEMENTDATE' IS NOT NULL
  AND (raw_payload->>'REGIONID') IN ('NSW1', 'QLD1', 'SA1', 'TAS1', 'VIC1')

{% if is_incremental() %}
  AND (raw_payload->>'SETTLEMENTDATE')::TIMESTAMPTZ > (SELECT COALESCE(MAX(time), '1900-01-01') FROM {{ this }})
{% endif %}
