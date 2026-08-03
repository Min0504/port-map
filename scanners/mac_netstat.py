"""macOS netstat -anv 기반 스캐너.

macOS에서 psutil.net_connections()가 AccessDenied를 반환할 때 폴백.
netstat -anv는 process:pid를 포함하므로 별도 tasklist 불필요.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any


def is_available() -> bool:
    return sys.platform == "darwin" and shutil.which("netstat") is not None


def scan(self_pid: int | None = None) -> dict[str, Any]:
    if not is_available():
        return {
            "ports": [], "scanned_at": _now(), "scanner": "mac_netstat",
            "count": 0, "error": "unavailable",
        }
    try:
        out = subprocess.run(
            ["netstat", "-anv"], capture_output=True, text=True, timeout=5,
        ).stdout
    except subprocess.TimeoutExpired:
        return {
            "ports": [], "scanned_at": _now(), "scanner": "mac_netstat",
            "count": 0, "error": "timeout",
        }

    ports: list[dict[str, Any]] = []
    for line in out.splitlines():
        if "LISTEN" not in line:
            continue
        parts = line.split()
        if len(parts) < 8:
            continue
        proto = parts[0]  # tcp4 / tcp6 / udp4 / udp6
        local = parts[3]  # Local Address
        # process:pid는 마지막 근처 필드에서 name:pid 패턴 찾기
        proc_pid = _find_proc_pid(parts)

        port = _parse_port(local)
        if port is None:
            continue

        pid = proc_pid[1] if proc_pid else None
        if self_pid is not None and pid == self_pid:
            continue

        ports.append({
            "port": port,
            "protocol": "tcp" if proto.startswith("tcp") else "udp",
            "family": "ipv6" if proto.endswith("6") else "ipv4",
            "state": "LISTEN",
            "pid": pid,
            "process": proc_pid[0] if proc_pid else "unknown",
            "cmdline": None,
            "remote": None,
            "permission": "full",
        })

    # 포트+family 기준 중복 제거 (IPv4/IPv6 동시 리스닝)
    seen: set[tuple[int, str]] = set()
    unique: list[dict[str, Any]] = []
    for p in ports:
        key = (p["port"], p["family"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(p)

    unique.sort(key=lambda p: (p["port"], p["family"]))
    return {
        "ports": unique, "scanned_at": _now(), "scanner": "mac_netstat",
        "count": len(unique), "error": None,
    }


_PROC_PID_RE = re.compile(r"^(.+):(\d+)$")


def _find_proc_pid(parts: list[str]) -> tuple[str, int] | None:
    """필드 중 name:pid 패턴 찾기."""
    for field in parts:
        m = _PROC_PID_RE.match(field)
        if m and m.group(2).isdigit():
            return m.group(1), int(m.group(2))
    return None


def _parse_port(local: str) -> int | None:
    # macOS netstat: 127.0.0.1.9749 또는 *.9749 (포트가 마지막 . 뒤)
    if "." not in local:
        return None
    port_s = local.rsplit(".", 1)[-1]
    try:
        return int(port_s)
    except ValueError:
        return None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
