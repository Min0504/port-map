# Port Map

> 로컬 포트 점유 현황을 실시간으로 보여주는 데스크톱 위젯

![Port Map](assets/screenshot.png)

바탕화면에 항상 떠 있는 반투명 미니 패널로, 어떤 포트를 어떤 프로세스가 쓰고 있는지 한눈에 볼 수 있습니다.

## 기능

- **실시간 포트:프로세스 표시** — 3초 폴링, 카드 그리드
- **검색** — 포트번호 / 프로세스명 즉시 필터
- **항상 위** — 다른 창 위에 떠 있음 (토글 가능)
- **프레임리스 반투명** — 위젯 느낌, 드래그로 위치 이동
- **더블클릭 확장** — PID, 전체 명령어, 원격 연결 정보
- **시스템 트레이** — 숨기기/보이기/종료
- **위치 기억** — 재실행 시 마지막 위치/크기 복원
- **크로스플랫폼** — macOS, Windows, Linux

## 설치

```bash
git clone https://github.com/Min0504/port-map.git
cd port-map
pip install -r requirements.txt
```

또는 uv 사용 (권장):

```bash
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python -r requirements.txt
```

## 실행

```bash
python app.py
```

옵션:

```bash
python app.py --interval 5 --opacity 0.8 --scanner psutil --click-through
```

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--interval` | 3 | 폴링 주기 (1~30초) |
| `--opacity` | 0.85 | 창 투명도 (0.6~0.95) |
| `--scanner` | auto | psutil / lsof / netstat |
| `--port` | 0 | HTTP 바인딩 포트 (0=자동) |
| `--no-on-top` | false | 항상 위 해제 |
| `--click-through` | false | 위젯 클릭통과 모드 |

환경변수: `PORT_MAP_INTERVAL` (폴링 주기)

## 설정 파일

`~/.config/port-map/config.json`에 창 위치/크기/설정이 저장됩니다.

## 빌드 (바이너리)

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name port-map --add-data "static:static" --add-data "scanners:scanners" app.py
```

## 미서명 실행 안내

### macOS
Gatekeeper가 "확인되지 않은 개발자" 경고를 띄웁니다:
1. Finder에서 port-map 우클릭 → "열기" → "열기" 확인
2. 또는 `xattr -cr /path/to/port-map.app`

### Windows
SmartScreen 경고 → "추가 정보" → "실행" 클릭.

## 기술 스택

- **pywebview** — 네이티브 창 (frameless, always-on-top, 드래그)
- **psutil** — 크로스플랫폼 포트 스캔 (권장)
- **netstat / lsof** — 폴백 스캐너
- **Python stdlib http.server** — 백엔드 (의존성 0)
- **Vanilla HTML/CSS/JS** — 프론트엔드 (프레임워크 없음)

## 아키텍처

```
┌──────────────┐     HTTP 127.0.0.1     ┌──────────────┐
│  index.html  │ ←── fetch /api/ports ─→ │   server.py  │
│  (pywebview) │     JSON 스냅샷         │ ThreadingHTTP│
└──────────────┘                        └──────┬───────┘
                                               │
                                        ┌──────▼───────┐
                                        │  scanners/   │
                                        │  psutil(권장)│
                                        │  netstat(폴백)│
                                        └──────────────┘
```

자세한 내용은 [PLANNING.md](PLANNING.md) 참조.

## 기여

[CONTRIBUTING.md](CONTRIBUTING.md)를 참조하세요.

## 라이선스

MIT — [LICENSE](LICENSE)
