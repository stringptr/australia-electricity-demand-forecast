
      
        delete from "electricity"."silver_silver"."features_ml" as DBT_INTERNAL_DEST
        where (time, region_id) in (
            select distinct time, region_id
            from "features_ml__dbt_tmp095323101278" as DBT_INTERNAL_SOURCE
        );

    

    insert into "electricity"."silver_silver"."features_ml" ("time", "region_id", "demand_mw", "temperature_2m", "relative_humidity_2m", "precipitation", "cloud_cover", "wind_speed_10m", "shortwave_radiation", "hour", "day_of_week", "is_weekend", "month", "season", "season_name", "updated_at")
    (
        select "time", "region_id", "demand_mw", "temperature_2m", "relative_humidity_2m", "precipitation", "cloud_cover", "wind_speed_10m", "shortwave_radiation", "hour", "day_of_week", "is_weekend", "month", "season", "season_name", "updated_at"
        from "features_ml__dbt_tmp095323101278"
    )
  