# Port Map

> 로컬 포트 점유 현황을 실시간으로 보여주는 데스크톱 위젯

바탕화면에 항상 떠 있는 반투명 미니 패널로, 어떤 포트를 어떤 프로세스가 쓰고 있는지 한눈에 볼 수 있습니다.

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

## 미서명 실행 안내

### macOS
Gatekeeper가 "확인되지 않은 개발자" 경고를 띄웁니다:
1. Finder에서 port-map 우클릭 → "열기" → "열기" 확인
2. 또는 `xattr -cr /path/to/port-map` 실행

### Windows
SmartScreen 경고 → "추가 정보" → "실행" 클릭.

## 기술 스택

- **pywebview** — 네이티브 창 (frameless, always-on-top)
- **psutil** — 크로스플랫폼 포트 스캔 (권장)
- **lsof / netstat** — psutil 미설치 시 폴백
- **Python stdlib http.server** — 백엔드 (의존성 0)

## 라이선스

MIT
