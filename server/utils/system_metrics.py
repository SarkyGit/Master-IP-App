import os
import time
from typing import Any, Dict

try:
    import psutil
except Exception:  # pragma: no cover - optional dependency
    psutil = None


def gather_metrics() -> Dict[str, Any]:
    """Collect system and application metrics."""
    if psutil is None:
        return {"error": "psutil not installed"}

    cpu_total = psutil.cpu_percent()
    cpu_per_core = psutil.cpu_percent(percpu=True)
    vm = psutil.virtual_memory()
    load1, load5, load15 = os.getloadavg()
    net_io = psutil.net_io_counters(pernic=True)
    network = {
        iface: {"bytes_sent": stats.bytes_sent, "bytes_recv": stats.bytes_recv}
        for iface, stats in net_io.items()
    }
    disk = None
    try:
        d = psutil.disk_io_counters()
        if d:
            disk = {"read_bytes": d.read_bytes, "write_bytes": d.write_bytes}
    except Exception:
        disk = None
    workers = []
    for proc in psutil.process_iter(["pid", "cmdline", "cpu_percent", "create_time"]):
        cmd = " ".join(proc.info.get("cmdline") or [])
        if "gunicorn" in cmd:
            try:
                cpu = proc.cpu_percent(interval=None)
                uptime = time.time() - proc.info["create_time"]
            except Exception:
                cpu = 0
                uptime = 0
            workers.append({"pid": proc.info["pid"], "cpu_percent": cpu, "uptime": uptime})
    metrics = {
        "cpu_total": cpu_total,
        "cpu_per_core": cpu_per_core,
        "memory": {"total": vm.total, "used": vm.used, "percent": vm.percent},
        "load_average": {"1": load1, "5": load5, "15": load15},
        "network": network,
        "disk": disk,
        "gunicorn_workers": len(workers),
        "worker_stats": workers,
    }
    return metrics
