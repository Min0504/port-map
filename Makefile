# Port Map Makefile
PYTHON := .venv/bin/python

## 빌드 (아이콘 포함)
build:
	./build.sh

## 실행 (개발 모드)
run:
	$(PYTHON) app.py

## 바이너리 실행
bin:
	./dist/port-map

## 테스트
test:
	$(PYTHON) tests/test_scanners.py

## 가상환경 설정
setup:
	uv venv --python 3.13 .venv
	uv pip install --python .venv/bin/python -r requirements.txt pyinstaller pillow

## 정리
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

.PHONY: build run bin test setup clean
