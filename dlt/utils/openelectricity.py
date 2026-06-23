import logging
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Generator

from openelectricity import OEClient
from openelectricity.types import MarketMetric

logger = logging.getLogger(__name__)

REGIONS = {"NSW1", "QLD1", "SA1", "TAS1", "VIC1"}

MAX_RANGE_DAYS = 8
LOOKBACK_MINUTES_REALTIME = 30


def _get_client() -> OEClient:
    api_key = os.environ.get("OPENELECTRICITY_API_KEY", "changemechangemechangemec")
    return OEClient(api_key=api_key)


def _region_from_name(name: str) -> str:
    for r in REGIONS:
        if name.endswith(f"_{r}"):
            return r
    return ""


def fetch_demand_chunk(date_start: datetime, date_end: datetime) -> list[dict]:
    rows: list[dict] = []
    response = _get_client().get_market(
        network_code="NEM",
        metrics=[MarketMetric.DEMAND],
        interval="5m",
        date_start=date_start,
        date_end=date_end,
        primary_grouping="network_region",
    )
    if not response.data:
        return rows

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
                rows.append(
                    {
                        "time": dt,
                        "region_id": region_id,
                        "demand_mw": float(value) if value is not None else None,
                    }
                )
    return rows


def fetch_demand_range(
    date_start: datetime, date_end: datetime
) -> Generator[list[dict], None, None]:
    current = date_start
    while current < date_end:
        chunk_end = min(current + timedelta(days=MAX_RANGE_DAYS - 1), date_end)
        logger.info("CHUNK: %s to %s", current.date(), chunk_end.date())
        rows = fetch_demand_chunk(current, chunk_end)
        if rows:
            yield rows
        current = chunk_end + timedelta(days=1)


def fetch_new_data() -> tuple[list[dict], dict | None]:
    STATE_FILE = (
        Path(__file__).resolve().parents[1] / "state" / "openelectricity_realtime.json"
    )

    def _load_state() -> dict:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text())
            except Exception:
                pass
        return {
            "last_processed_interval": "1900-01-01T00:00:00+10:00",
            "updated_at": None,
        }

    def _save_state(state: dict) -> None:
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, indent=2))

    state = _load_state()
    last_interval = datetime.fromisoformat(state["last_processed_interval"])

    date_start = datetime.now() - timedelta(minutes=LOOKBACK_MINUTES_REALTIME)
    logger.info("FETCH: demand data from %s", date_start.isoformat())

    rows = fetch_demand_chunk(date_start, datetime.now())

    new_rows = [r for r in rows if r["time"] > last_interval]
    if not new_rows:
        logger.info("FILTERED: 0 new rows (since %s)", state["last_processed_interval"])
        return [], None

    max_interval = max(r["time"] for r in new_rows)
    new_state = {"last_processed_interval": max_interval.isoformat()}
    _save_state(new_state)

    logger.info(
        "RESULT: %d new rows (since %s), advanced to %s",
        len(new_rows),
        state["last_processed_interval"],
        new_state["last_processed_interval"],
    )
    return new_rows, new_state
