
      
        delete from "electricity"."silver"."demand_5min" as DBT_INTERNAL_DEST
        where (time, region_id) in (
            select distinct time, region_id
            from "demand_5min__dbt_tmp013608015743" as DBT_INTERNAL_SOURCE
        );

    

    insert into "electricity"."silver"."demand_5min" ("time", "demand_mw", "updated_at", "region_id")
    (
        select "time", "demand_mw", "updated_at", "region_id"
        from "demand_5min__dbt_tmp013608015743"
    )
  