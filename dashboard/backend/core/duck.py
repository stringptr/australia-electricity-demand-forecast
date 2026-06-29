import duckdb
from core.config import settings

_duck: duckdb.DuckDBPyConnection | None = None


def get_duck() -> duckdb.DuckDBPyConnection:
    global _duck
    if _duck is None:
        _duck = duckdb.connect()
        _duck.execute(f"ATTACH '{settings.DATABASE_URL}' AS pg (TYPE POSTGRES, SCHEMA gold)")
    return _duck


async def close_duck():
    global _duck
    if _duck is not None:
        _duck.close()
        _duck = None
