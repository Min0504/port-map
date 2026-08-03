"""스캐너 선택 라우터. psutil 우선, 실패 시 OS별 폴백."""
from __future__ import annotations

import sys
from typing import Any

from . import base, mac_linux, mac_netstat, windows

_ORDER = {
    "auto": [base, mac_netstat, mac_linux, windows],
    "psutil": [base],
    "lsof": [mac_linux],
    "netstat": [windows, mac_netstat],
}


def get_scanner():
    """가용한 첫 스캐너 반환."""
    for s in _ORDER["auto"]:
        if s.is_available():
            return s
    return base


def scan(self_pid: int | None = None, preferred: str = "auto") -> dict[str, Any]:
    """포트 스캔. preferred로 스캐너 강제 선택 가능.

    preferred: 'auto' | 'psutil' | 'lsof' | 'netstat'
    """
    candidates = _ORDER.get(preferred, _ORDER["auto"])
    last_error: str | None = None
    for scanner in candidates:
        if not scanner.is_available():
            continue
        result = scanner.scan(self_pid)
        if not result["error"]:
            return result
        last_error = result["error"]
    # 전부 실패 — 마지막 에러 반환
    return {
        "ports": [], "scanned_at": _now_str(), "scanner": "none",
        "count": 0, "error": last_error or "no_scanner_available",
    }


def _now_str() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
