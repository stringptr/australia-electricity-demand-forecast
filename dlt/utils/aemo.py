import os
import io
import csv
import zipfile
import logging
from pathlib import Path
from typing import Generator

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


def _upload_csv(content: str, key: str) -> None:
    s3 = _get_s3()
    body = content.encode("utf-8")
    s3.put_object(Bucket=S3_BUCKET, Key=key, Body=body)
    logger.info("S3 PUT: s3://%s/%s (%d bytes) uploaded", S3_BUCKET, key, len(body))


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


def iter_month_files(year: int, month: int) -> Generator[list[dict], None, None]:
    """Download ZIP, yield filtered rows per DISPATCHDEMAND CSV file."""
    url = f"{NEMWEB_BASE}/{year}/MMSDM_{year}_{month:02d}.zip"
    logger.info("DOWNLOAD: Starting %s", url)

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    tmp_zip = TMP_DIR / f"MMSDM_{year}_{month:02d}.zip"

    with httpx.Client(timeout=httpx.Timeout(300), follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
        tmp_zip.write_bytes(resp.content)

    logger.info("DOWNLOADED: %s (%d bytes) → %s", url, len(resp.content), tmp_zip)

    uploaded = 0
    total_rows = 0

    with zipfile.ZipFile(tmp_zip) as zf:
        dispatch_csvs = [name for name in sorted(zf.namelist())
                        if "DISPATCHDEMAND" in name.upper() and name.upper().endswith(".CSV")]

        logger.info("ZIP SCAN: %s → found %d DISPATCHDEMAND CSV(s): %s", tmp_zip.name, len(dispatch_csvs), dispatch_csvs)

        for name in dispatch_csvs:
            try:
                logger.info("EXTRACT: reading %s from ZIP ...", name)
                csv_text = zf.read(name).decode("utf-8", errors="replace")
                logger.info("EXTRACTED: %s (%d bytes raw CSV)", name, len(csv_text))
                logger.info("PARSE: processing CSV rows from %s ...", name)
                rows = _parse_dispatch_csv(csv_text)
                logger.info("PARSED: %s → %d valid rows", name, len(rows))

                s3_key = f"MMSDM/{year}/{month:02d}/{Path(name).name}"
                buf = io.StringIO()
                writer = csv.DictWriter(buf, fieldnames=["time", "region_id", "total_demand"])
                writer.writeheader()
                writer.writerows(rows)
                _upload_csv(buf.getvalue(), s3_key)
                uploaded += 1
                total_rows += len(rows)

                yield rows
            except Exception:
                logger.exception("FAILED: parse/upload %s in ZIP", name)

    tmp_zip.unlink()

    if total_rows == 0:
        logger.warning("SKIP: no DISPATCHDEMAND rows found for %d-%02d", year, month)
        return

    logger.info("MONTH %d-%02d complete: %d files uploaded, %d total rows", year, month, uploaded, total_rows)


