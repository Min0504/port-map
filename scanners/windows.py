"""netstat + tasklist 기반 폴백 스캐너 (Windows, psutil 미설치 시)."""
from __future__ import annotations

import shutil
import subprocess
from datetime import datetime, timezone
from typing import Any


def is_available() -> bool:
    return shutil.which("netstat") is not None


def scan(self_pid: int | None = None) -> dict[str, Any]:
    if not is_available():
        return {
            "ports": [], "scanned_at": _now(), "scanner": "netstat",
            "count": 0, "error": "netstat_not_found",
        }
    try:
        out = subprocess.run(
            ["netstat", "-ano"], capture_output=True, text=True, timeout=5,
        ).stdout
    except subprocess.TimeoutExpired:
        return {
            "ports": [], "scanned_at": _now(), "scanner": "netstat",
            "count": 0, "error": "timeout",
        }

    # PID -> 프로세스명 맵 (tasklist로 보강)
    pid_names = _tasklist_map()

    ports: list[dict[str, Any]] = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 5 or "LISTENING" not in line:
            continue
        # proto local foreign state pid
        proto, local, _foreign, state, pid_s = parts[0], parts[1], parts[2], parts[3], parts[4]
        try:
            pid = int(pid_s)
        except ValueError:
            continue
        if self_pid is not None and pid == self_pid:
            continue
        port = _parse_port(local)
        if port is None:
            continue
        ports.append({
            "port": port, "protocol": proto.lower().replace("6", ""),
            "family": "ipv6" if "[" in local else "ipv4",
            "state": "LISTEN", "pid": pid,
            "process": pid_names.get(pid, "unknown"),
            "cmdline": None, "remote": None, "permission": "full",
        })

    ports.sort(key=lambda p: (p["port"], p["family"]))
    return {
        "ports": ports, "scanned_at": _now(), "scanner": "netstat",
        "count": len(ports), "error": None,
    }


def _tasklist_map() -> dict[int, str]:
    if not shutil.which("tasklist"):
        return {}
    try:
        out = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=5,
        ).stdout
    except subprocess.TimeoutExpired:
        return {}
    result: dict[int, str] = {}
    for line in out.splitlines():
        # "name","pid","session","sessionnum","mem"
        fields = line.strip('"').split('","')
        if len(fields) >= 2:
            try:
                result[int(fields[1])] = fields[0]
            except ValueError:
                continue
    return result


def _parse_port(local: str) -> int | None:
    if ":" not in local:
        return None
    port_s = local.rsplit(":", 1)[-1]
    try:
        return int(port_s)
    except ValueError:
        return None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
