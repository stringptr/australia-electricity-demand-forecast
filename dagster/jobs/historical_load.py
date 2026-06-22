import subprocess
import sys

sys.path.insert(0, "/opt/dagster/dlt")

from dagster import StaticPartitionsDefinition, job, op

partitions = StaticPartitionsDefinition(["2026"])


@op
def load_demand_op(context) -> None:
    year = int(context.partition_key)
    from pipelines.demand_aemo import run_demand_pipeline

    context.log.info("Starting AEMO demand load for year %d", year)
    run_demand_pipeline(year)
    context.log.info("AEMO demand load complete for year %d", year)


@op
def load_weather_op(context) -> None:
    year = int(context.partition_key)
    from pipelines.weather_openmeteo import run_weather_pipeline

    context.log.info("Starting OpenMeteo weather load for year %d", year)
    run_weather_pipeline(year)
    context.log.info("OpenMeteo weather load complete for year %d", year)


@op
def dbt_run_op(context) -> None:
    context.log.info("Running DBT silver models")
    subprocess.run(
        ["dbt", "run", "--models", "silver", "--profiles-dir", "/opt/dagster/dbt"],
        cwd="/opt/dagster/dbt",
        check=True,
    )
    context.log.info("DBT run complete")


@job(
    partitions_def=partitions,
    description="Historical backfill: DLT bronze → DBT silver",
)
def historical_backfill() -> None:
    load_demand_op()
    load_weather_op()
    dbt_run_op()
