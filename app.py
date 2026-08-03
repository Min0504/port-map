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
    "theme": "dark",           # dark | light
    "favorites": [],           # 고정할 포트 리스트 [3000, 8080, ...]
    "sound_alert": True,        # 새 포트 점유 시 사운드 알림
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
    p.add_argument("--theme", default=None, choices=["dark", "light"],
                   help="Color theme (default: dark)")
    p.add_argument("--no-sound", action="store_true",
                   help="Disable sound alert on new port")
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
    if args.theme:
        cfg["theme"] = args.theme
    if args.no_sound:
        cfg["sound_alert"] = False

    # 백엔드 HTTP 서버 (백그라운드 스레드)
    server = PortMapServer(port=args.port, preferred_scanner=args.scanner)
    server.start_background()
    actual_port = server.actual_port
    print(f"[Port Map] server on http://127.0.0.1:{actual_port}", flush=True)

    import urllib.parse
    qp = urllib.parse.urlencode({
        "interval": cfg["interval"],
        "opacity": args.opacity,
        "theme": cfg.get("theme", "dark"),
        "sound": str(cfg.get("sound_alert", True)).lower(),
    })
    url = f"http://127.0.0.1:{actual_port}/?{qp}"

    # width/height가 0이면 기본값 사용 (이전 실행에서 0이 저장된 경우 방지)
    win_w = cfg["width"] if cfg["width"] and cfg["width"] > 100 else 320
    win_h = cfg["height"] if cfg["height"] and cfg["height"] > 100 else 480

    window = webview.create_window(
        title="Port Map",
        url=url,
        width=win_w,
        height=win_h,
        x=cfg["x"],
        y=cfg["y"],
        resizable=True,
        frameless=True,
        easy_drag=False,  # 커스텀 드래그 핸들 사용 (특정 영역만 드래그)
        on_top=cfg["on_top"],
        transparent=False,
    )

    # ── 창 제어 API (JS에서 호출) ──
    # expose는 창 생성 직후, webview.start() 전에 호출해야 안정적
    def close_window():
        """위젯 종료 — 창 닫기 + 서버 종료 + 프로세스 종료."""
        try:
            # 위치/크기 저장 (on_closed가 호출되지 않을 수 있으므로 직접 저장)
            new_cfg = dict(cfg)
            geom = window.evaluate_js(
                "[window.screenX, window.screenY, window.outerWidth, window.outerHeight]")
            if geom and len(geom) == 4:
                gw, gh = int(geom[2]), int(geom[3])
                new_cfg["x"], new_cfg["y"] = int(geom[0]), int(geom[1])
                # 0이거나 너무 작으면 저장하지 않음 (frameless 창에서 evaluate_js가 0 반환하는 문제)
                if gw > 100 and gh > 100:
                    new_cfg["width"], new_cfg["height"] = gw, gh
            save_config(new_cfg)
        except Exception:
            pass
        try:
            server.shutdown()
        except Exception:
            pass
        try:
            window.destroy()
        except Exception:
            pass
        # destroy()만으로는 프로세스가 종료되지 않으므로 명시적으로 exit
        import os
        os._exit(0)

    def minimize_window():
        """창 최소화/숨기기."""
        try:
            window.hide()
        except Exception:
            try:
                window.minimize()
            except Exception:
                pass

    def toggle_on_top():
        """항상 위 토글."""
        try:
            window.on_top = not getattr(window, '_on_top', True)
            return window.on_top
        except Exception:
            return None

    def save_setting(key, value):
        """설정 저장 (favorites, theme, sound_alert 등)."""
        try:
            new_cfg = dict(cfg)
            new_cfg[key] = value
            save_config(new_cfg)
            return True
        except Exception:
            return False

    # expose를 start() 전에 호출 — macOS에서 가장 안정적
    window.expose(close_window, minimize_window, toggle_on_top, save_setting)

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
                gw, gh = int(geom[2]), int(geom[3])
                new_cfg["x"], new_cfg["y"] = int(geom[0]), int(geom[1])
                if gw > 100 and gh > 100:
                    new_cfg["width"], new_cfg["height"] = gw, gh
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
