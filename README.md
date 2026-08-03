# Port Map

> 로컬 포트 점유 현황을 실시간으로 보여주는 데스크톱 위젯.

![License](https://img.shields.io/badge/license-MIT-blue) ![Python](https://img.shields.io/badge/python-3.9+-yellow) ![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey)

바탕화면에 항상 떠 있는 반투명 미니 패널로, 어떤 포트를 어떤 프로세스가 쓰고 있는지 한눈에 볼 수 있다.

## 기능

- **실시간 포트:프로세스 카드 그리드** — LISTEN 중인 포트를 포트번호순 카드로 표시 (`8080 : node`)
- **크로스플랫폼 스캐너** — psutil(권장), lsof, netstat 자동 폴백
- **프로토콜·권한 배지** — tcp/udp, root 권한 여부 표시
- **프레임리스 항상 위 창** — 반투명 패널로 작업 방해 없음
- **조정 가능한 폴링 주기·투명도** — CLI 옵션으로 설정

## 설치

```bash
pip install -r requirements.txt
```

## 실행

```bash
python app.py
```

옵션:

```bash
python app.py --interval 5 --opacity 0.8 --scanner psutil
```

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--interval` | 3 | 폴링 주기 (1~30초) |
| `--opacity` | 0.85 | 창 투명도 (0.6~0.95) |
| `--scanner` | auto | psutil / lsof / netstat |
| `--port` | 0 | HTTP 바인딩 포트 (0=자동) |

## 빌드 (바이너리)

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name port-map app.py
```

### 미서명 실행 안내

**macOS** — Gatekeeper가 "확인되지 않은 개발자" 경고를 띄웁니다:
1. Finder에서 port-map 우클릭 → "열기" → "열기" 확인
2. 또는 `xattr -cr /path/to/port-map` 실행

**Windows** — SmartScreen 경고 → "추가 정보" → "실행" 클릭.

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| 네이티브 창 | pywebview (frameless, always-on-top) |
| 포트 스캔 | psutil (권장), lsof / netstat 폴백 |
| 백엔드 | Python stdlib http.server (의존성 0) |
| UI | HTML/CSS (static/) |

## 프로젝트 구조

```text
.
├── app.py              진입점 — pywebview 창 실행
├── server.py           HTTP 백엔드 (stdlib http.server)
├── scanners/           포트 스캐너 추상화
│   ├── base.py         스캐너 인터페이스
│   ├── mac_linux.py    macOS/Linux (lsof)
│   ├── mac_netstat.py  macOS (netstat 폴백)
│   └── windows.py      Windows (netstat)
├── static/             프론트엔드 (index.html)
├── tests/              스캐너 테스트
├── requirements.txt
├── PLANNING.md         기획서
└── LICENSE             MIT
```

## 기여

이슈와 PR은 환영합니다. 기획 배경과 기능 명세는 [PLANNING.md](PLANNING.md)를 참고하세요.

## 라이선스

MIT © 2026 채민석 (N167)
