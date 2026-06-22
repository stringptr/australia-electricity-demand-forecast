
      
        delete from "electricity"."silver_silver"."weather_hourly" as DBT_INTERNAL_DEST
        where (time, region_id) in (
            select distinct time, region_id
            from "weather_hourly__dbt_tmp204704141529" as DBT_INTERNAL_SOURCE
        );

    

    insert into "electricity"."silver_silver"."weather_hourly" ("time", "region_id", "temperature_2m", "relative_humidity_2m", "precipitation", "cloud_cover", "wind_speed_10m", "shortwave_radiation", "updated_at")
    (
        select "time", "region_id", "temperature_2m", "relative_humidity_2m", "precipitation", "cloud_cover", "wind_speed_10m", "shortwave_radiation", "updated_at"
        from "weather_hourly__dbt_tmp204704141529"
    )
  