
      
        delete from "electricity"."silver_silver"."demand_5min" as DBT_INTERNAL_DEST
        where (time, region_id) in (
            select distinct time, region_id
            from "demand_5min__dbt_tmp204704147264" as DBT_INTERNAL_SOURCE
        );

    

    insert into "electricity"."silver_silver"."demand_5min" ("time", "region_id", "demand_mw", "updated_at")
    (
        select "time", "region_id", "demand_mw", "updated_at"
        from "demand_5min__dbt_tmp204704147264"
    )
  