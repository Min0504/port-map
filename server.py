"""HTTP 서버 + 스캐너 호출 라우터.

PLANNING.md 4/5/8절 기반. 127.0.0.1 전용, 포트 0(ephemeral), SIGPIPE 방지,
ThreadingHTTPServer, 자기 포트 필터링.
"""
from __future__ import annotations

import json
import os
import signal
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from scanners import scan as scan_ports

STATIC_DIR = Path(__file__).parent / "static"
_last_snapshot: dict[str, Any] | None = None
_fail_count = 0


def _ignore_sigpipe() -> None:
    if (sigpipe := getattr(signal, "SIGPIPE", None)) is not None:
        signal.signal(sigpipe, signal.SIG_IGN)


class Handler(BaseHTTPRequestHandler):
    server_pid: int | None = None
    preferred_scanner: str = "auto"

    def log_message(self, *args: Any) -> None:
        pass  # 로그 억제 (위젯 도구)

    def do_GET(self) -> None:
        if self.path == "/api/ports":
            self._serve_ports()
        elif self.path == "/api/health":
            self._serve_health()
        elif self.path == "/" or self.path == "/index.html":
            self._serve_static("index.html", "text/html")
        else:
            self.send_error(404)

    def _serve_ports(self) -> None:
        global _last_snapshot, _fail_count
        try:
            snapshot = scan_ports(self_pid=self.server_pid,
                                  preferred=self.preferred_scanner)
            _last_snapshot = snapshot
            _fail_count = 0
        except Exception as exc:
            _fail_count += 1
            snapshot = _last_snapshot or {
                "ports": [], "scanned_at": "", "scanner": "unknown",
                "count": 0, "error": f"scan_failed: {exc}",
            }
            snapshot = dict(snapshot)
            snapshot["error"] = f"scan_failed: {exc}"
        self._json(snapshot)

    def _serve_health(self) -> None:
        self._json({
            "status": "ok",
            "scanner": _last_snapshot["scanner"] if _last_snapshot else "none",
            "last_scan": _last_snapshot["scanned_at"] if _last_snapshot else None,
            "fail_count": _fail_count,
        })

    def _serve_static(self, name: str, mime: str) -> None:
        path = STATIC_DIR / name
        if not path.exists():
            self.send_error(404)
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except BrokenPipeError:
            pass

    def _json(self, data: dict[str, Any]) -> None:
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except BrokenPipeError:
            pass


class PortMapServer:
    def __init__(self, port: int = 0, preferred_scanner: str = "auto") -> None:
        _ignore_sigpipe()
        self.httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self.httpd.daemon_threads = True
        Handler.server_pid = os.getpid()
        Handler.preferred_scanner = preferred_scanner

    @property
    def actual_port(self) -> int:
        return self.httpd.server_address[1]

    def start_background(self) -> None:
        t = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        t.start()

    def shutdown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()


def run_standalone(port: int = 0) -> None:
    """app.py 없이 단독 실행 시 (개발/테스트용)."""
    srv = PortMapServer(port=port)
    srv.start_background()
    print(f"Port Map server on http://127.0.0.1:{srv.actual_port}")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    run_standalone()
