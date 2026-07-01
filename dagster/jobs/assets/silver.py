import os

from dagster import AssetExecutionContext
from dagster_dbt import DagsterDbtTranslator, DbtCliResource, dbt_assets

MANIFEST_PATH = os.environ.get(
    "DBT_MANIFEST_PATH",
    "/opt/dagster/dbt/target/manifest.json",
)


class SilverTranslator(DagsterDbtTranslator):
    @classmethod
    def get_group_name(cls, dbt_resource_props) -> str:
        return "silver"


@dbt_assets(
    manifest=MANIFEST_PATH,
    dagster_dbt_translator=SilverTranslator(),
)
def dbt_silver_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    yield from dbt.cli(["run", "--select", "silver"], context=context).stream()
