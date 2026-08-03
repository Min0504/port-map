#!/bin/bash
# Port Map 설치 스크립트
# 사용법: ./install.sh

set -e
cd "$(dirname "$0")"

echo "══════════════════════════════════════"
echo "  Port Map 설치"
echo "══════════════════════════════════════"

# 의존성 확인
if ! command -v python3 &> /dev/null; then
    echo "✗ Python 3가 필요합니다. https://python.org"
    exit 1
fi

# uv 권장, 없으면 venv
if command -v uv &> /dev/null; then
    echo "▶ uv로 가상환경 생성..."
    uv venv --python 3.13 .venv 2>/dev/null || uv venv .venv
    uv pip install --python .venv/bin/python -r requirements.txt
else
    echo "▶ python venv로 가상환경 생성..."
    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt
fi

# 빌드
echo "▶ 빌드 시작..."
./build.sh

echo ""
echo "══════════════════════════════════════"
echo "  ✓ 설치 완료!"
echo "══════════════════════════════════════"

# 전역 명령어 등록
echo "▶ 전역 명령어 등록 중..."
LOCAL_BIN="$HOME/.local/bin"
mkdir -p "$LOCAL_BIN"
ln -sf "$PWD/bin/portmap" "$LOCAL_BIN/portmap"
echo "  ✓ portmap → $LOCAL_BIN/portmap"

echo ""
echo "실행 방법:"
echo "  전역:  portmap              # 어디서든 실행 가능"
echo "  개발:  .venv/bin/python app.py"
echo "  빌드:  ./dist/port-map"
if [ -d "dist/port-map.app" ]; then
    echo "  앱:    open dist/port-map.app"
fi
echo ""
echo "옵션:"
echo "  --interval 5     폴링 주기 (초)"
echo "  --opacity 0.8    창 투명도"
echo "  --click-through  위젯 클릭통과 모드"
echo ""
if ! echo "$PATH" | grep -q "$LOCAL_BIN"; then
    echo "※ PATH에 $LOCAL_BIN 이 없습니다. 추가하려면:"
    echo "    echo 'export PATH=\"$HOME/.local/bin:$PATH\"' >> ~/.zshrc && source ~/.zshrc"
fi
