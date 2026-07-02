import logging
import os
import sys
import time
import urllib.request
import urllib.error

sys.path.insert(0, "/app")

from shared.alerts import send_alert

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("health-monitor")

CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", "60"))
POSTGRES_HOST = os.environ.get("PG_HOST", "postgres")
POSTGRES_PORT = int(os.environ.get("PG_PORT", "5432"))
NATS_URL = os.environ.get("NATS_URL", "nats://nats:8222")
DEBEZIUM_URL = os.environ.get("DEBEZIUM_URL", "http://debezium-server:8080")
VM_URL = os.environ.get("VM_URL", "http://victoriametrics:8428")

_failures: dict[str, int] = {}
FAILURE_THRESHOLD = 2


def _http_get(url: str, timeout: int = 5) -> bool:
    try:
        resp = urllib.request.urlopen(url, timeout=timeout)
        return 200 <= resp.status < 400
    except Exception:
        return False


def _check_postgres() -> bool:
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect((POSTGRES_HOST, POSTGRES_PORT))
        s.close()
        return True
    except Exception:
        return False


def _check_nats() -> bool:
    return _http_get(f"http://{NATS_URL.split('//')[-1]}/healthz")


def _check_debezium() -> bool:
    return _http_get(f"{DEBEZIUM_URL}/q/health/ready", timeout=5)


def _check_victoriametrics() -> bool:
    return _http_get(f"{VM_URL}/-/healthy")


def _check_vm_disk() -> bool:
    try:
        url = f"{VM_URL}/api/v1/query?query=min(vm_free_disk_space_bytes)"
        resp = urllib.request.urlopen(url, timeout=5)
        data = resp.json()
        results = data.get("data", {}).get("result", [])
        if results:
            free_bytes = float(results[0]["value"][1])
            free_gb = free_bytes / (1024 ** 3)
            if free_gb < 1.0:
                send_alert(
                    f"VictoriaMetrics disk low: *{free_gb:.1f}GB* free",
                    level="CRITICAL",
                    throttle_key="vm_disk_low",
                    throttle_seconds=1800,
                )
                return False
        return True
    except Exception:
        return True


def _check_inference_staleness() -> bool:
    try:
        url = f"{VM_URL}/api/v1/query?query=max(demand_staleness_seconds)"
        resp = urllib.request.urlopen(url, timeout=5)
        data = resp.json()
        results = data.get("data", {}).get("result", [])
        if results:
            staleness = float(results[0]["value"][1])
            if staleness > 900:
                send_alert(
                    f"Inference staleness alert from VM: *{int(staleness)}s*",
                    level="WARNING",
                    throttle_key="vm_staleness",
                    throttle_seconds=600,
                )
                return False
        return True
    except Exception:
        return True


def _alert_if_persistent(name: str, ok: bool) -> None:
    if ok:
        _failures.pop(name, None)
        return
    _failures[name] = _failures.get(name, 0) + 1
    if _failures[name] == FAILURE_THRESHOLD:
        send_alert(
            f"Service *{name}* is DOWN (failed {FAILURE_THRESHOLD} consecutive checks)",
            level="CRITICAL",
            throttle_key=f"monitor_{name}",
            throttle_seconds=600,
        )
    elif _failures[name] > FAILURE_THRESHOLD and _failures[name] % 10 == 0:
        send_alert(
            f"Service *{name}* still DOWN ({_failures[name]} consecutive failures)",
            level="CRITICAL",
            throttle_key=f"monitor_{name}",
            throttle_seconds=600,
        )


def run_checks() -> None:
    checks = [
        ("PostgreSQL", _check_postgres),
        ("NATS", _check_nats),
        ("Debezium", _check_debezium),
        ("VictoriaMetrics", _check_victoriametrics),
    ]
    for name, check_fn in checks:
        ok = check_fn()
        _alert_if_persistent(name, ok)

    _check_vm_disk()
    _check_inference_staleness()


def main() -> None:
    logger.info(
        "Health monitor started (interval=%ds, threshold=%d)",
        CHECK_INTERVAL,
        FAILURE_THRESHOLD,
    )
    while True:
        try:
            run_checks()
        except Exception as e:
            logger.exception("Health check loop error: %s", e)
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
