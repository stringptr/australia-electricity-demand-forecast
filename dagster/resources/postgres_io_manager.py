import os

import pandas as pd
from dagster import ConfigurableIOManager
from sqlalchemy import create_engine


class PostgresIOManager(ConfigurableIOManager):
    host: str = os.environ.get("PG_HOST", os.environ.get("POSTGRES_HOST", "postgres"))
    port: int = int(os.environ.get("PG_PORT", os.environ.get("POSTGRES_PORT", "5432")))
    user: str = os.environ.get("PG_USER", os.environ.get("POSTGRES_USER", "postgres"))
    password: str = os.environ.get("PG_PASSWORD", os.environ.get("POSTGRES_PASSWORD", "postgres"))
    database: str = os.environ.get("PG_DB", os.environ.get("POSTGRES_DB", "electricity"))

    def _get_engine(self):
        url = f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        return create_engine(url, connect_args={"connect_timeout": 10})

    def handle_output(self, context, obj):
        if obj is None or (isinstance(obj, pd.DataFrame) and obj.empty):
            context.log.debug("No rows to write, skipping")
            return

        key_path = context.asset_key.path
        if len(key_path) >= 2:
            schema = key_path[-2]
            table = key_path[-1]
        else:
            schema = "public"
            table = key_path[-1]

        engine = self._get_engine()
        with engine.begin() as conn:
            obj.to_sql(
                table,
                conn,
                schema=schema,
                if_exists="append",
                index=False,
                method="multi",
            )

        context.log.info(f"Wrote {len(obj)} rows to {schema}.{table}")
        context.add_output_metadata(
            {"rows_written": len(obj), "table": f"{schema}.{table}"}
        )

    def load_input(self, context) -> pd.DataFrame:
        key_path = context.asset_key.path
        if len(key_path) >= 2:
            schema = key_path[-2]
            table = key_path[-1]
        else:
            schema = "public"
            table = key_path[-1]

        engine = self._get_engine()
        with engine.connect() as conn:
            return pd.read_sql_table(table, conn, schema=schema)
