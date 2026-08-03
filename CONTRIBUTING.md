# Contributing to Port Map

Port Map은 작은 오픈소스 프로젝트입니다. 기여를 환영합니다.

## 개발 환경

```bash
git clone https://github.com/Min0504/port-map.git
cd port-map
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python app.py
```

## 기여 방법

1. 이슈를 먼저 확인하거나 생성합니다.
2. 브랜치: `feat/기능명` 또는 `fix/버그명`
3. 커밋 메시지: 한글 또는 영문, 의미 있게
4. PR 생성 — 변경점과 테스트 방법을 설명

## 코드 스타일

- Python: PEP 8, 타입 힌트 권장
- JS: Vanilla, 프레임워크 없음
- 함수/변수명: 명확하게, 약어 지양

## 테스트

```bash
.venv/bin/python tests/test_scanners.py
```

## 라이선스

기여는 MIT 라이선스로 배포됩니다.
