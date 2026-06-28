
      
  
    

  create  table "electricity"."silver_silver"."demand_5min"
  
  
    as
  
  (
    

SELECT
    time,
    region_id,
    demand_mw,
    NOW() AS updated_at
FROM "electricity"."bronze"."demand"
WHERE demand_mw IS NOT NULL
  AND time IS NOT NULL
  AND region_id IN ('NSW1', 'QLD1', 'SA1', 'TAS1', 'VIC1')


  );
  
  