import csv
import io
import logging
import os
import re
import shutil
import zipfile
from datetime import datetime, timezone

from zoneinfo import ZoneInfo

import httpx
import dlt
import psycopg2

logger = logging.getLogger(__name__)

NEMWEB_URL = "https://www.nemweb.com.au/REPORTS/CURRENT/DispatchIS_Reports/"
REGIONS = {"NSW1", "QLD1", "SA1", "TAS1", "VIC1"}

REGION_MAP = {
    "NEW SOUTH WALES": "NSW1",
    "QUEENSLAND": "QLD1",
    "SOUTH AUSTRALIA": "SA1",
    "TASMANIA": "TAS1",
    "VICTORIA": "VIC1",
}


def _parse_settlement_time(fname: str) -> datetime:
    ts = fname.split("_")[2]
    dt = datetime.strptime(ts, "%Y%m%d%H%M")
    dt = dt.replace(tzinfo=ZoneInfo("Australia/Sydney"))
    return dt.astimezone(timezone.utc)


def _list_remote_files() -> list[tuple[str, datetime]]:
    resp = httpx.get(NEMWEB_URL, timeout=30)
    resp.raise_for_status()

    files = []
    for line in resp.text.splitlines():
        for m in re.finditer(
            r"(\w+,\s+\w+\s+\d+,\s+\d{4}\s+\d{2}:\d{2}\s+(AM|PM))"
            r"\s+\d+\s+<A HREF=\"[^\"]*?"
            r"(PUBLIC_DISPATCHIS_\d{12}_\d+\.zip)"
            r"\">",
            line,
        ):
            fname = m.group(3)
            try:
                settlement_time = _parse_settlement_time(fname)
            except (IndexError, ValueError):
                continue
            files.append((fname, settlement_time))
    return files


def _parse_dispatch_csv(text: str) -> list[dict]:
    rows = []
    header = None
    reader = csv.reader(text.splitlines())
    for line in reader:
        if not line:
            continue
        prefix = line[0]

        if prefix == "C":
            continue
        elif prefix == "I":
            header = [c.strip().upper() for c in line[1:]]
        elif prefix == "D":
            if header is None:
                continue
            if len(line[1:]) != len(header):
                continue
            if len(line) < 2 or line[2].strip() != "REGIONSUM":
                continue
            row = dict(zip(header, line[1:]))
            rows.append(row)
        elif prefix == "F":
            continue
    return rows


def _extract_demand_rows(parsed: list[dict]) -> list[dict]:
    results = []
    for row in parsed:
        region_raw = row.get("REGIONID", "").strip()
        region_id = REGION_MAP.get(region_raw.upper(), region_raw)
        if region_id not in REGIONS:
            continue

        raw_time = row.get("SETTLEMENTDATE", "")
        if not raw_time:
            continue

        try:
            time_val = datetime.fromisoformat(raw_time)
        except ValueError:
            try:
                time_val = datetime.strptime(raw_time, "%Y/%m/%d %H:%M:%S")
            except ValueError:
                continue

        if time_val.tzinfo is None:
            time_val = time_val.replace(tzinfo=ZoneInfo("Australia/Sydney"))
        time_val = time_val.astimezone(timezone.utc)

        try:
            demand_mw = float(row.get("TOTALDEMAND", ""))
        except (ValueError, TypeError):
            continue

        if demand_mw < 0:
            continue

        results.append(
            {
                "time": time_val,
                "region_id": region_id,
                "demand_mw": demand_mw,
            }
        )
    return results


def _fetch_and_parse_file(fname: str) -> list[dict]:
    url = NEMWEB_URL + fname
    logger.info("Fetching %s", url)
    resp = httpx.get(url, timeout=30)
    resp.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        csv_name = zf.namelist()[0]
        text = zf.read(csv_name).decode("utf-8-sig")

    parsed = _parse_dispatch_csv(text)
    demand_rows = _extract_demand_rows(parsed)
    logger.info("Parsed %d demand rows from %s", len(demand_rows), fname)
    return demand_rows


def _get_latest_processed_time(conn) -> datetime | None:
    with conn.cursor() as cur:
        cur.execute("SELECT MAX(time) FROM bronze.demand")
        return cur.fetchone()[0]


def run_nemweb_pipeline() -> list[dict]:
    files = _list_remote_files()
    if not files:
        logger.warning("No files found on NEMWEB")
        return []

    files.sort(key=lambda x: x[1], reverse=True)

    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "electricity"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
    )

    try:
        last_time = _get_latest_processed_time(conn)
    finally:
        conn.close()

    if last_time is not None:
        logger.info("Latest data in DB: %s", last_time)
        files_to_process = [(f, t) for f, t in files if t > last_time]
        if not files_to_process:
            logger.info("No files with settlement > %s", last_time)
            return []
    else:
        files_to_process = files[:1]

    all_rows = []
    for fname, _ in files_to_process:
        try:
            rows = _fetch_and_parse_file(fname)
            all_rows.extend(rows)
        except Exception as e:
            logger.warning("Failed to process %s: %s", fname, e)
            continue

    if not all_rows:
        return []

    max_time = max(r["time"] for r in all_rows)
    pipelines_dir = "/tmp/dlt/demand_nemweb"
    if os.path.exists(pipelines_dir):
        shutil.rmtree(pipelines_dir)

    pipeline = dlt.pipeline(
        pipeline_name="demand_nemweb",
        destination="postgres",
        dataset_name="bronze",
        pipelines_dir=pipelines_dir,
    )
    pipeline.run(
        all_rows,
        table_name="demand",
        write_disposition="merge",
        primary_key=("time", "region_id"),
    )

    logger.info(
        "Loaded %d rows into bronze.demand (latest: %s)", len(all_rows), max_time
    )
    return all_rows
