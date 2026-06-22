import os
import io
import csv
import zipfile
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import boto3
import httpx

logger = logging.getLogger(__name__)

NEMWEB_BASE = "https://nemweb.com.au/Data_Archive/Wholesale_Electricity/MMSDM"
REGIONS = {"NSW1", "QLD1", "SA1", "TAS1", "VIC1"}
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "http://garage:3900")
S3_BUCKET = os.getenv("S3_BUCKET", "aemo-nemweb")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "aemo-key-id")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "aemo-secret-key")
S3_REGION = os.getenv("S3_REGION", "us-east-1")
MAX_WORKERS = 4
TMP_DIR = Path("/tmp/aemo")

s3_client = None


def _get_s3():
    global s3_client
    if s3_client is None:
        s3_client = boto3.client(
            "s3",
            endpoint_url=S3_ENDPOINT,
            aws_access_key_id=S3_ACCESS_KEY,
            aws_secret_access_key=S3_SECRET_KEY,
            region_name=S3_REGION,
        )
    return s3_client


def _s3_key(year: int, month: int) -> str:
    return f"MMSDM/{year}/{month:02d}.csv"


def _upload_csv(content: str, year: int, month: int) -> str:
    s3 = _get_s3()
    key = _s3_key(year, month)
    s3.put_object(Bucket=S3_BUCKET, Key=key, Body=content.encode("utf-8"))
    logger.info("Uploaded s3://%s/%s", S3_BUCKET, key)
    return key


def _parse_dispatch_csv(csv_text: str) -> list[dict]:
    """Parse DISPATCHDEMAND CSV, yield rows for 5 states."""
    rows = []
    reader = csv.DictReader(io.StringIO(csv_text))
    for row in reader:
        region_id = (row.get("REGIONID") or "").strip().upper()
        if region_id not in REGIONS:
            continue
        dispatch_type = (row.get("DISPATCH") or "").strip()
        if dispatch_type != "DISPATCH":
            continue
        settlement_date = (row.get("SETTLEMENTDATE") or "").strip()
        total_demand = (row.get("TOTALDEMAND") or "").strip()
        if not settlement_date or not total_demand:
            continue
        rows.append(
            {
                "time": settlement_date,
                "region_id": region_id,
                "total_demand": total_demand,
            }
        )
    return rows


def _download_and_extract(year: int, month: int) -> list[dict]:
    """Download ZIP, extract DISPATCHDEMAND CSVs, upload combined CSV to S3."""
    url = f"{NEMWEB_BASE}/{year}/MMSDM_{year}_{month:02d}.zip"
    logger.info("Downloading %s", url)

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    tmp_zip = TMP_DIR / f"MMSDM_{year}_{month:02d}.zip"

    with httpx.Client(timeout=httpx.Timeout(300), follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
        tmp_zip.write_bytes(resp.content)

    all_rows = []
    dispatch_csvs = []

    with zipfile.ZipFile(tmp_zip) as zf:
        for name in sorted(zf.namelist()):
            if "DISPATCHDEMAND" not in name.upper():
                continue
            if not name.upper().endswith(".CSV"):
                continue
            dispatch_csvs.append(name)

        for name in dispatch_csvs:
            try:
                csv_text = zf.read(name).decode("utf-8", errors="replace")
                rows = _parse_dispatch_csv(csv_text)
                all_rows.extend(rows)
            except Exception:
                logger.exception("Failed to parse %s in ZIP", name)

    tmp_zip.unlink()

    if not all_rows:
        logger.warning("No DISPATCHDEMAND rows found for %d-%02d", year, month)
        return []

    combined = io.StringIO()
    writer = csv.DictWriter(combined, fieldnames=["time", "region_id", "total_demand"])
    writer.writeheader()
    writer.writerows(all_rows)

    _upload_csv(combined.getvalue(), year, month)
    logger.info("Month %d-%02d: %d rows", year, month, len(all_rows))
    return all_rows


def process_year(year: int, start_month: int = 1, end_month: int = 12) -> list[dict]:
    """Download and parse all months in a year, parallel download (4 workers)."""
    from datetime import datetime

    current = datetime.now()
    actual_end = end_month
    if year == current.year:
        actual_end = min(end_month, current.month)
    if year > current.year:
        return []

    months = list(range(start_month, actual_end + 1))
    all_rows = []
    failed = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_map = {executor.submit(_download_and_extract, year, mn): mn for mn in months}
        for future in as_completed(future_map):
            mn = future_map[future]
            try:
                rows = future.result()
                all_rows.extend(rows)
                logger.info("OK %d-%02d: %d rows", year, mn, len(rows))
            except Exception:
                logger.exception("FAIL %d-%02d", year, mn)
                failed.append(mn)

    logger.info(
        "Year %d summary: %d months OK, %d failed, total %d rows",
        year,
        len(months) - len(failed),
        len(failed),
        len(all_rows),
    )
    return all_rows
