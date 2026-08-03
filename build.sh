#!/bin/bash
# Port Map 빌드 스크립트 (macOS/Windows/Linux 공통)
# 사용법: ./build.sh

set -e
cd "$(dirname "$0")"

echo "▶ 의존성 확인..."
if [ ! -d ".venv" ]; then
    if command -v uv &> /dev/null; then
        uv venv --python 3.13 .venv
        uv pip install --python .venv/bin/python -r requirements.txt pyinstaller pillow
    elif command -v python3 &> /dev/null; then
        python3 -m venv .venv
        .venv/bin/pip install -r requirements.txt pyinstaller pillow
    else
        echo "✗ Python 3 이 필요합니다"
        exit 1
    fi
fi

PYTHON=".venv/bin/python"
PIP_INSTALL=".venv/bin/pip"
if [ -n "$(command -v uv)" ]; then
    PIP_INSTALL="uv pip install --python .venv/bin/python"
fi

echo "▶ 아이콘 생성..."
$PYTHON -c "
from PIL import Image, ImageDraw, ImageFont
import os
size = 1024
img = Image.new('RGBA', (size, size), (0,0,0,0))
draw = ImageDraw.Draw(img)
draw.rounded_rectangle([80,80,size-80,size-80], radius=160, fill=(20,22,28,255), outline=(91,157,255,255), width=8)
cx, cy = size//2, size//2-40
draw.rounded_rectangle([cx-180,cy-140,cx+180,cy+140], radius=40, fill=(40,44,52,255), outline=(91,157,255,200), width=6)
for i in range(4):
    px = cx-120+i*80
    draw.rounded_rectangle([px-24,cy-80,px+24,cy+60], radius=12, fill=(91,157,255,255))
try:
    font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 200)
except:
    font = ImageFont.load_default()
text='PM'
bbox = draw.textbbox((0,0), text, font=font)
draw.text((cx-(bbox[2]-bbox[0])//2, size-300-(bbox[3]-bbox[1])//2), text, fill=(227,228,230,255), font=font)
img.save('assets/icon.png')
os.makedirs('assets/icon.iconset', exist_ok=True)
for s in [16,32,64,128,256,512,1024]:
    img.resize((s,s), Image.LANCZOS).save(f'assets/icon.iconset/icon_{s}x{s}.png')
    if s<=512: img.resize((s*2,s*2), Image.LANCZOS).save(f'assets/icon.iconset/icon_{s}x{s}@2x.png')
print('icon created')
" 2>/dev/null || echo "  (아이콘 스킵 — Pillow 없음)"

# macOS icns 변환
if [ "$(uname)" = "Darwin" ] && [ -d "assets/icon.iconset" ]; then
    iconutil -c icns assets/icon.iconset -o assets/icon.icns 2>/dev/null && echo "  icns 변환 완료" || true
fi

echo "▶ PyInstaller 빌드..."
ICNS_ARG=""
if [ -f "assets/icon.icns" ]; then
    ICNS_ARG="--icon assets/icon.icns --add-data assets/icon.icns:assets --windowed"
fi

.venv/bin/pyinstaller --onefile --name port-map -y \
    --add-data "static:static" \
    --add-data "scanners:scanners" \
    $ICNS_ARG \
    app.py

# macOS: Info.plist로 앱 이름/아이콘 설정
if [ -f "dist/port-map.app/Contents/Info.plist" ] && [ -f "assets/Info.plist" ]; then
    cp assets/Info.plist dist/port-map.app/Contents/Info.plist
    echo "  Info.plist 적용 — 앱 이름: Port Map"
fi

echo ""
echo "✓ 빌드 완료!"
echo "  바이너리: dist/port-map"
if [ -d "dist/port-map.app" ]; then
    echo "  앱 번들: dist/port-map.app"
fi
echo ""
echo "실행: ./dist/port-map  또는  open dist/port-map.app"
