"""pywebview 진입점 — 백그라운드 HTTP 서버 + 창 실행.

PLANNING.md 4/8절. 단일 프로세스, 서버는 백그라운드 스레드.
"""
from __future__ import annotations

import argparse
import os
import sys
import threading
import time

import webview

from server import PortMapServer


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Port Map — desktop port widget")
    p.add_argument("--port", type=int, default=0,
                   help="HTTP bind port (0=ephemeral, default)")
    p.add_argument("--interval", type=int, default=3,
                   help="Polling interval seconds (1-30)")
    p.add_argument("--opacity", type=float, default=0.85,
                   help="Window opacity 0.6-0.95")
    p.add_argument("--scanner", default="auto",
                   choices=["auto", "psutil", "lsof", "netstat"],
                   help="Port scanner backend")
    args = p.parse_args()
    if not (1 <= args.interval <= 30):
        p.error("--interval must be 1-30")
    if not (0.6 <= args.opacity <= 0.95):
        p.error("--opacity must be 0.6-0.95")
    return args


def main() -> None:
    args = parse_args()
    env_interval = os.environ.get("PORT_MAP_INTERVAL")
    if env_interval:
        try:
            args.interval = max(1, min(30, int(env_interval)))
        except ValueError:
            pass

    # 백엔드 HTTP 서버 (백그라운드 스레드)
    server = PortMapServer(port=args.port, preferred_scanner=args.scanner)
    server.start_background()
    url = f"http://127.0.0.1:{server.actual_port}?interval={args.interval}"

    # pywebview 창 — frameless, 항상 위, 반투명
    window = webview.create_window(
        title="Port Map",
        url=url,
        width=320,
        height=480,
        resizable=True,
        frameless=True,
        easy_drag=False,  # 커스텀 드래그 핸들 사용
        on_top=True,
    )
    # 투명도는 JS에서 배경 rgba로 제어 (opacity 인자는 query로 전달)

    def on_closed():
        server.shutdown()

    try:
        webview.start()
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
