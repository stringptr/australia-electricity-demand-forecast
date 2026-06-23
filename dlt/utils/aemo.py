import os
import io
import csv
import zipfile
import logging
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

s3_client = None


class RangeHTTPFile:
    def __init__(self, url: str):
        self._url = url
        self._size: int | None = None
        self._pos = 0
        self._client = httpx.Client(timeout=httpx.Timeout(300), follow_redirects=True)
        self._closed = False

    def _ensure_size(self) -> int:
        if self._size is None:
            resp = self._client.head(self._url)
            resp.raise_for_status()
            self._size = int(resp.headers["Content-Length"])
        return self._size

    def read(self, size: int = -1) -> bytes:
        if self._closed or size == 0:
            return b""
        end = self._pos + size - 1 if size > 0 else self._ensure_size() - 1
        headers = {"Range": f"bytes={self._pos}-{end}"}
        resp = self._client.get(self._url, headers=headers)
        resp.raise_for_status()
        data = resp.content
        self._pos += len(data)
        return data

    def seek(self, offset: int, whence: int = 0) -> int:
        if whence == 0:
            self._pos = offset
        elif whence == 1:
            self._pos += offset
        elif whence == 2:
            self._pos = self._ensure_size() + offset
        return self._pos

    def tell(self) -> int:
        return self._pos

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def close(self) -> None:
        self._closed = True
        self._client.close()


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
    """Stream DISPATCHDEMAND entries from remote ZIP via HTTP Range."""
    url = f"{NEMWEB_BASE}/{year}/MMSDM_{year}_{month:02d}.zip"
    logger.info("OPEN REMOTE ZIP: %s", url)

    fh = RangeHTTPFile(url)
    with zipfile.ZipFile(fh) as zf:
        dispatch_csvs = [
            name for name in sorted(zf.namelist())
            if "DISPATCHDEMAND" in name.upper() and name.upper().endswith(".CSV")
        ]

        logger.info(
            "ZIP SCAN: %d DISPATCHDEMAND CSV(s) found in remote ZIP: %s",
            len(dispatch_csvs),
            dispatch_csvs,
        )

        uploaded = 0
        total_rows = 0

        for name in dispatch_csvs:
            try:
                logger.info("EXTRACT: reading %s from remote ZIP ...", name)
                csv_text = zf.read(name).decode("utf-8", errors="replace")
                logger.info("EXTRACTED: %s (%d bytes raw CSV)", name, len(csv_text))

                logger.info("PARSE: processing CSV rows from %s ...", name)
                rows = _parse_dispatch_csv(csv_text)
                logger.info("PARSED: %s → %d valid rows", name, len(rows))

                s3_key = f"MMSDM/{year}/{month:02d}/{name.rsplit('/', 1)[-1]}"
                buf = io.StringIO()
                writer = csv.DictWriter(buf, fieldnames=["time", "region_id", "total_demand"])
                writer.writeheader()
                writer.writerows(rows)
                _upload_csv(buf.getvalue(), s3_key)
                uploaded += 1
                total_rows += len(rows)

                yield rows
            except Exception:
                logger.exception("FAILED: parse/upload %s in remote ZIP", name)

    if total_rows == 0:
        logger.warning("SKIP: no DISPATCHDEMAND rows found for %d-%02d", year, month)
        return

    logger.info(
        "MONTH %d-%02d complete: %d files uploaded, %d total rows",
        year, month, uploaded, total_rows,
    )


