import logging

import dlt

from utils.openelectricity import fetch_new_data

logger = logging.getLogger(__name__)


def run_realtime_pipeline() -> bool:
    rows, new_state = fetch_new_data()

    if not rows or new_state is None:
        return False

    pipeline = dlt.pipeline(
        pipeline_name="demand_openelectricity",
        destination="postgres",
        dataset_name="bronze",
    )

    pipeline.run(
        rows,
        table_name="demand",
        write_disposition="merge",
        primary_key=("time", "region_id"),
    )

    logger.info("LOADED: %d rows into bronze.demand", len(rows))
    return True
