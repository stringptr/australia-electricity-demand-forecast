import os

from dagster import AssetExecutionContext
from dagster_dbt import DbtCliResource, dbt_assets

MANIFEST_PATH = os.environ.get(
    "DBT_MANIFEST_PATH",
    "/opt/dagster/dbt/target/manifest.json",
)


@dbt_assets(manifest=MANIFEST_PATH)
def dbt_silver_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    yield from dbt.cli(["run", "--select", "silver"], context=context).stream()
