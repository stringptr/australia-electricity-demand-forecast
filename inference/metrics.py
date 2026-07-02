import logging
import os
import time
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

VM_URL = os.environ.get(
    "VM_URL", "http://victoriametrics:8428/api/v1/import/prometheus"
)

last_demand_time: dict[str, float] = {}


def _fmt_labels(labels: dict | None) -> str:
    if not labels:
        return ""
    return ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))


def push(name: str, value: float, labels: dict | None = None) -> None:
    label_str = _fmt_labels(labels)
    now = int(time.time())
    line = f"{name}{{{label_str}}} {value} {now}\n"
    try:
        req = urllib.request.Request(
            VM_URL,
            data=line.encode(),
            headers={"Content-Type": "text/plain"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        logger.warning("Failed to push %s to VM: %s", name, e)


_counters: dict[str, float] = {}


def increment(name: str, labels: dict | None = None) -> None:
    key = f"{name}{'|' + str(labels) if labels else ''}"
    _counters[key] = _counters.get(key, 0) + 1
    push(name, _counters[key], labels)
