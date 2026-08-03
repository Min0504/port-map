"""Port Map — 데스크톱 포트 위젯 진입점.

오픈소스(MIT). 단일 프로세스에서 백그라운드 HTTP 서버 + pywebview 창 실행.
기능: frameless, always-on-top, 드래그 이동, 위치/크기 기억, 위젯 모드(클릭통과).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import webview

from server import PortMapServer

CONFIG_DIR = Path.home() / ".config" / "port-map"
CONFIG_FILE = CONFIG_DIR / "config.json"
DEFAULT_CONFIG = {
    "x": 2640, "y": 100, "width": 320, "height": 480,
    "on_top": True, "click_through": False, "interval": 3,
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Port Map — desktop port widget")
    p.add_argument("--port", type=int, default=0, help="HTTP bind port (0=ephemeral)")
    p.add_argument("--interval", type=int, default=None, help="Polling interval 1-30s")
    p.add_argument("--opacity", type=float, default=0.85, help="Window opacity 0.6-0.95")
    p.add_argument("--scanner", default="auto",
                   choices=["auto", "psutil", "lsof", "netstat"], help="Scanner backend")
    p.add_argument("--no-on-top", action="store_true", help="Disable always-on-top")
    p.add_argument("--click-through", action="store_true",
                   help="Widget click-through mode (mouse events pass through)")
    args = p.parse_args()
    if args.interval is not None and not (1 <= args.interval <= 30):
        p.error("--interval must be 1-30")
    if not (0.6 <= args.opacity <= 0.95):
        p.error("--opacity must be 0.6-0.95")
    return args


def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_FILE.exists():
        try:
            cfg.update(json.loads(CONFIG_FILE.read_text()))
        except (json.JSONDecodeError, OSError):
            pass
    return cfg


def save_config(cfg: dict) -> None:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(cfg, indent=2))
    except OSError:
        pass


def main() -> None:
    args = parse_args()
    cfg = load_config()

    # 환경변수 오버라이드
    env_interval = os.environ.get("PORT_MAP_INTERVAL")
    if env_interval:
        try:
            cfg["interval"] = max(1, min(30, int(env_interval)))
        except ValueError:
            pass
    if args.interval is not None:
        cfg["interval"] = args.interval
    if args.no_on_top:
        cfg["on_top"] = False
    if args.click_through:
        cfg["click_through"] = True

    # 백엔드 HTTP 서버 (백그라운드 스레드)
    server = PortMapServer(port=args.port, preferred_scanner=args.scanner)
    server.start_background()
    actual_port = server.actual_port
    print(f"[Port Map] server on http://127.0.0.1:{actual_port}", flush=True)

    params = f"?interval={cfg['interval']}&opacity={args.opacity}"
    url = f"http://127.0.0.1:{actual_port}/{params}"

    window = webview.create_window(
        title="Port Map",
        url=url,
        width=cfg["width"],
        height=cfg["height"],
        x=cfg["x"],
        y=cfg["y"],
        resizable=True,
        frameless=True,
        easy_drag=False,  # 커스텀 드래그 핸들 사용 (특정 영역만 드래그)
        on_top=cfg["on_top"],
        transparent=False,
    )

    def on_loaded():
        # 창 위치 강제 이동 (pywebview x/y가 macOS에서 무시되는 문제 보정)
        if cfg.get("x") is not None and cfg.get("y") is not None:
            try:
                window.move(cfg["x"], cfg["y"])
            except Exception:
                pass
        # 항상 위 강제 적용
        if cfg.get("on_top"):
            try:
                window.on_top = True
            except Exception:
                pass
        # 위젯 모드: click-through 적용 (마우스 이벤트가 창을 통과)
        if cfg.get("click_through"):
            try:
                window.evaluate_js(
                    "document.body.style.pointerEvents='none';"
                    "document.getElementById('drag-handle').style.pointerEvents='auto';"
                    "document.getElementById('search').style.pointerEvents='auto';"
                    "document.getElementById('grid').style.pointerEvents='auto';"
                )
            except Exception:
                pass

    def on_closed():
        # 위치/크기 저장
        try:
            new_cfg = dict(cfg)
            geom = window.evaluate_js(
                "[window.screenX, window.screenY, window.outerWidth, window.outerHeight]")
            if geom and len(geom) == 4:
                new_cfg["x"], new_cfg["y"] = int(geom[0]), int(geom[1])
                new_cfg["width"], new_cfg["height"] = int(geom[2]), int(geom[3])
            save_config(new_cfg)
        except Exception:
            pass
        server.shutdown()

    window.events.loaded += on_loaded
    window.events.closed += on_closed

    try:
        webview.start()
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
