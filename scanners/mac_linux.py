"""lsof 기반 폴백 스캐너 (macOS/Linux, psutil 미설치 시)."""
from __future__ import annotations

import shutil
import subprocess
from datetime import datetime, timezone
from typing import Any


def is_available() -> bool:
    return shutil.which("lsof") is not None


def scan(self_pid: int | None = None) -> dict[str, Any]:
    if not is_available():
        return {
            "ports": [], "scanned_at": _now(), "scanner": "lsof",
            "count": 0, "error": "lsof_not_found",
        }
    try:
        out = subprocess.run(
            ["lsof", "-iTCP", "-sTCP:LISTEN", "-P", "-n"],
            capture_output=True, text=True, timeout=5,
        ).stdout
    except subprocess.TimeoutExpired:
        return {
            "ports": [], "scanned_at": _now(), "scanner": "lsof",
            "count": 0, "error": "timeout",
        }

    ports: list[dict[str, Any]] = []
    for line in out.strip().splitlines()[1:]:  # 헤더 스킵
        parts = line.split()
        if len(parts) < 9:
            continue
        name, pid_s = parts[0], parts[1]
        # 자기 포트 필터링
        try:
            pid = int(pid_s)
        except ValueError:
            continue
        if self_pid is not None and pid == self_pid:
            continue
        # name:addr 형식에서 포트 추출 (예: *:8080)
        local = parts[8]
        port = _parse_port(local)
        if port is None:
            continue
        ports.append({
            "port": port, "protocol": "tcp",
            "family": "ipv6" if "[" in local or ":" in local.split(".")[-1] else "ipv4",
            "state": "LISTEN", "pid": pid, "process": name,
            "cmdline": None, "remote": None, "permission": "full",
        })

    ports.sort(key=lambda p: (p["port"], p["family"]))
    return {
        "ports": ports, "scanned_at": _now(), "scanner": "lsof",
        "count": len(ports), "error": None,
    }


def _parse_port(local: str) -> int | None:
    # 형식: 1.2.3.4:8080, *:8080, [::]:8080 등
    if ":" not in local:
        return None
    port_s = local.rsplit(":", 1)[-1]
    try:
        return int(port_s)
    except ValueError:
        return None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
