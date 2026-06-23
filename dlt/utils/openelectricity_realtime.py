import logging
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

from openelectricity import OEClient
from openelectricity.types import MarketMetric

logger = logging.getLogger(__name__)

REGIONS_MAP = {"NSW1", "QLD1", "SA1", "TAS1", "VIC1"}
STATE_FILE = Path(__file__).resolve().parents[1] / "state" / "openelectricity_realtime.json"

LOOKBACK_MINUTES = 30
NORMAL_INTERVAL_S = 300


def _get_client() -> OEClient:
    api_key = os.environ.get("OPENELECTRICITY_API_KEY", "oe_5enewJGbCyjWDRkvKd3UNp")
    return OEClient(api_key=api_key)


def _default_state() -> dict:
    return {
        "last_processed_interval": "1900-01-01T00:00:00+10:00",
        "updated_at": None,
    }


def _load_state() -> dict:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            logger.warning("Failed to parse state file, starting fresh")
            return _default_state()
    return _default_state()


def _save_state(state: dict) -> None:
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def _region_from_name(name: str) -> str:
    for r in REGIONS_MAP:
        if name.endswith(f"_{r}"):
            return r
    return ""


def fetch_new_data() -> tuple[list[dict], dict | None]:
    state = _load_state()
    last_interval_str = state["last_processed_interval"]
    last_interval = datetime.fromisoformat(last_interval_str)

    client = _get_client()
    date_start = datetime.now() - timedelta(minutes=LOOKBACK_MINUTES)

    logger.info("FETCH: demand data from %s", date_start.isoformat())

    response = client.get_market(
        network_code="NEM",
        metrics=[MarketMetric.DEMAND],
        interval="5m",
        date_start=date_start,
        primary_grouping="network_region",
    )

    if not response.data:
        logger.info("No data returned from API")
        return [], None

    all_rows: list[dict] = []
    max_interval = last_interval

    for ts in response.data:
        for result in ts.results:
            region_id = _region_from_name(result.name)
            if not region_id:
                continue

            for dp in result.data:
                dt, value = dp.root
                if dt.tzinfo is None:
                    from pendulum import timezone
                    dt = dt.replace(tzinfo=timezone("Australia/Sydney"))

                if dt <= last_interval:
                    continue

                all_rows.append({
                    "interval": dt,
                    "region_id": region_id,
                    "operational_demand": float(value),
                })

                if dt > max_interval:
                    max_interval = dt

    if not all_rows:
        logger.info("FILTERED: 0 new rows (since %s)", last_interval_str)
        return [], None

    new_state = {
        "last_processed_interval": max_interval.isoformat(),
    }

    _save_state(new_state)

    logger.info("RESULT: %d new rows (since %s), advanced to %s",
                len(all_rows), last_interval_str, new_state["last_processed_interval"])

    return all_rows, new_state


def transform_row(row: dict) -> dict:
    return {
        "time": row["interval"],
        "region_id": row["region_id"],
        "raw_payload": {
            "INTERVAL_DATETIME": row["interval"].isoformat(),
            "REGIONID": row["region_id"],
            "OPERATIONAL_DEMAND": row["operational_demand"],
            "SOURCE": "OPENElectricity",
        },
    }
