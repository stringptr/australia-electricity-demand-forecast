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
    invocation = dbt.cli(["run"], context=context)
    try:
        yield from invocation.stream()
    except Exception:
        try:
            context.log.error(f"dbt returncode: {invocation.process.returncode}")
            out = invocation.process.stdout.read().decode() if invocation.process.stdout else ""
            err = invocation.process.stderr.read().decode() if invocation.process.stderr else ""
            context.log.error(f"dbt stdout:\n{out[:5000]}")
            if err:
                context.log.error(f"dbt stderr:\n{err[:5000]}")
        except Exception as log_err:
            context.log.error(f"Could not capture dbt output: {log_err}")
        raise
