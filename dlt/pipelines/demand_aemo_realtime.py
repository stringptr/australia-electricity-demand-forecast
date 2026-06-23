import logging

import dlt

from utils.openelectricity_realtime import fetch_new_data, transform_row

logger = logging.getLogger(__name__)


def run_realtime_pipeline() -> bool:
    rows, new_state = fetch_new_data()

    if not rows or new_state is None:
        logger.info("No new data to load")
        return False

    pipeline = dlt.pipeline(
        pipeline_name="demand_openelectricity",
        destination="postgres",
        dataset_name="bronze",
    )

    pipeline.run(
        (transform_row(r) for r in rows),
        table_name="demand",
        write_disposition="merge",
        primary_key=("time", "region_id"),
    )

    logger.info("PIPELINE: loaded %d rows into bronze.demand", len(rows))
    return True
