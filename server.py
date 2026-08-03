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

# PyInstaller 번들(sys._MEIPASS)과 일반 실행 모두 지원
if hasattr(sys, "_MEIPASS"):
    STATIC_DIR = Path(sys._MEIPASS) / "static"
else:
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
        # query string 분리 (예: /?interval=3&opacity=0.85 -> /)
        path = self.path.split("?", 1)[0]
        if path == "/api/ports":
            self._serve_ports()
        elif path == "/api/health":
            self._serve_health()
        elif path == "/" or path == "/index.html":
            self._serve_static("index.html", "text/html")
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/api/kill":
            self._handle_kill()
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

    def _handle_kill(self) -> None:
        """포트 점유 프로세스 종료. PID 정수 검증 후 os.kill 직접 호출.

        보안: shell=True 금지, PID는 반드시 정수. 명령어 주입 방지.
        """
        import os
        import signal
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else b"{}"
            data = json.loads(body)
        except (json.JSONDecodeError, ValueError):
            self._json({"ok": False, "error": "invalid_json"})
            return

        pid = data.get("pid")
        # PID 정수 검증 — 문자열/객체 거부 (주입 방지)
        if not isinstance(pid, int) or pid <= 0:
            self._json({"ok": False, "error": "invalid_pid"})
            return

        # 자기 자신은 kill 금지
        if pid == self.server_pid:
            self._json({"ok": False, "error": "cannot_kill_self"})
            return

        try:
            os.kill(pid, signal.SIGTERM)
            self._json({"ok": True, "pid": pid})
        except ProcessLookupError:
            self._json({"ok": False, "error": "process_not_found"})
        except PermissionError:
            self._json({"ok": False, "error": "permission_denied",
                        "hint": "sudo 또는 관리자 권한 필요"})
        except OSError as exc:
            self._json({"ok": False, "error": f"os_error: {exc}"})


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
