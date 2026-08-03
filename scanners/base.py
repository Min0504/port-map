"""psutil 기반 크로스플랫폼 포트 스캐너 (권장).

psutil.net_connections() + Process 정보로 macOS/Windows/Linux 동일 API.
psutil 미설치 시 상위 라우터가 lsof/netstat 폴백으로 전환.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

try:
    import psutil
except ImportError:
    psutil = None  # type: ignore[assignment]


def is_available() -> bool:
    return psutil is not None


def scan(self_pid: int | None = None) -> dict[str, Any]:
    """포트 스냅샷 반환. self_pid는 앱 자신의 서버 PID (결과에서 제외).

    반환 형식은 PLANNING.md 5절 JSON 스키마를 따른다.
    """
    if psutil is None:
        return {
            "ports": [], "scanned_at": _now(), "scanner": "psutil",
            "count": 0, "error": "psutil_not_installed",
        }

    ports: list[dict[str, Any]] = []
    try:
        conns = psutil.net_connections(kind="inet")
    except psutil.AccessDenied:
        return {
            "ports": [], "scanned_at": _now(), "scanner": "psutil",
            "count": 0, "error": "access_denied",
        }

    for c in conns:
        laddr = c.laddr
        if not laddr or not laddr.port:
            continue
        pid = c.pid
        # 자기 포트 필터링 — 앱 자신의 서버 포트 노이즈 제거
        if self_pid is not None and pid == self_pid:
            continue

        process, cmdline, permission = _proc_info(pid)

        raddr = None
        if c.raddr:
            raddr = f"{c.raddr.ip}:{c.raddr.port}"

        ports.append({
            "port": laddr.port,
            "protocol": "tcp" if c.type == 1 else "udp",
            "family": "ipv4" if ":" not in laddr.ip else "ipv6",
            "state": _state_name(c.status),
            "pid": pid,
            "process": process,
            "cmdline": cmdline,
            "remote": raddr,
            "permission": permission,
        })

    # 포트번호 오름차순 정렬 (기본 정렬)
    ports.sort(key=lambda p: (p["port"], p["family"]))
    return {
        "ports": ports, "scanned_at": _now(), "scanner": "psutil",
        "count": len(ports), "error": None,
    }


def _proc_info(pid: int | None) -> tuple[str, str | None, str]:
    """PID로 프로세스명/cmdline/권한 상태 반환."""
    if pid is None:
        return "unknown", None, "limited"
    try:
        p = psutil.Process(pid)
        name = p.name()
    except psutil.NoSuchProcess:
        return "unknown", None, "limited"
    except psutil.AccessDenied:
        return "unknown", None, "denied"
    try:
        cmdline = " ".join(p.cmdline())
        if not cmdline:
            cmdline = None
        return name, cmdline, "full"
    except psutil.AccessDenied:
        return name, None, "denied"


def _state_name(status: str) -> str:
    mapping = {
        "LISTEN": "LISTEN", "NONE": "NONE", "ESTABLISHED": "ESTABLISHED",
        "TIME_WAIT": "TIME_WAIT", "CLOSE_WAIT": "CLOSE_WAIT",
        "FIN_WAIT1": "FIN_WAIT1", "FIN_WAIT2": "FIN_WAIT2",
        "SYN_SENT": "SYN_SENT", "SYN_RECV": "SYN_RECV",
        "CLOSING": "CLOSING", "LAST_ACK": "LAST_ACK",
    }
    return mapping.get(status, status)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
