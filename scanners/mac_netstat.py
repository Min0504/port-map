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

try:
    import psutil
except ImportError:
    psutil = None  # type: ignore[assignment]


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

        # psutil로 프로세스 정보 보강 (cmdline + 친근한 이름)
        proc_name, cmdline, permission = _enrich_process(pid, proc_pid[0] if proc_pid else None)

        ports.append({
            "port": port,
            "protocol": "tcp" if proto.startswith("tcp") else "udp",
            "family": "ipv6" if proto.endswith("6") else "ipv4",
            "state": "LISTEN",
            "pid": pid,
            "process": proc_name,
            "cmdline": cmdline,
            "remote": None,
            "permission": permission,
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


def _enrich_process(pid: int | None, fallback_name: str | None) -> tuple[str, str | None, str]:
    """psutil로 cmdline을 가져오고 친근한 프로세스명을 추출.

    node_modules/@org/pkg, python -m mod, uvicorn app:main 등에서
    핵심 패키지/모듈명을 추출해 사용자 친화적 이름을 만든다.
    """
    if pid is None or psutil is None:
        name = fallback_name or "unknown"
        return _friendly_name(name, None), None, "limited"
    try:
        p = psutil.Process(pid)
        raw_name = p.name()
        try:
            cmd_parts = p.cmdline()
        except psutil.AccessDenied:
            cmd_parts = []
    except psutil.NoSuchProcess:
        return fallback_name or "unknown", None, "limited"
    except psutil.AccessDenied:
        return fallback_name or "unknown", None, "denied"

    cmdline = " ".join(cmd_parts) if cmd_parts else None
    friendly = _friendly_name(raw_name, cmd_parts, fallback_name)
    perm = "full" if cmd_parts else "limited"
    return friendly, cmdline, perm


def _friendly_name(raw_name: str, cmd_parts: list[str] | None,
                   fallback: str | None = None) -> str:
    """실행 파일명보다 의미 있는 이름 추출.

    예: bun.exe .../node_modules/@bitkyc08/opencodex/... -> opencodex
        python app.py -> app
        node server.js -> server
    """
    if not cmd_parts:
        # 실행 파일명에서 .exe, 경로 제거
        name = (fallback or raw_name).split("/")[-1]
        return name.replace(".exe", "")

    full = " ".join(cmd_parts)

    # node_modules/@org/pkg 패턴
    import re
    m = re.search(r"node_modules/(@[\w.-]+/[\w.-]+)", full)
    if m:
        parts = m.group(1).split("/")
        # @org/pkg -> pkg (org가 의미 없으면)
        return parts[-1] if len(parts) > 1 else m.group(1)

    # node_modules/pkg 패턴
    m = re.search(r"node_modules/([\w.-]+)", full)
    if m:
        return m.group(1)

    # python -m module 패턴
    m = re.search(r"\-m\s+([\w.]+)", full)
    if m:
        return m.group(1).split(".")[-1]

    # uvicorn/gunicorn app:main 패턴
    m = re.search(r"(?:uvicorn|gunicorn)\s+([\w.:]+)", full)
    if m:
        return m.group(1).split(":")[0]

    # 일반: 마지막 .py/.ts/.js 파일명 (확장자 제거)
    for part in cmd_parts:
        if part.endswith((".py", ".ts", ".js")):
            return part.split("/")[-1].rsplit(".", 1)[0]

    # 실행 파일명에서 .exe, 경로 제거
    return raw_name.split("/")[-1].replace(".exe", "")
