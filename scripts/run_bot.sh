#!/bin/bash
# Slack Bot 실행 스크립트

cd "$(dirname "$0")"

echo "=========================================="
echo "  Tencent MCP Slack Bot 실행"
echo "=========================================="
echo

# 가상환경 활성화
if [ -d "venv" ]; then
    echo "✅ 가상환경 활성화 중..."
    source venv/bin/activate
else
    echo "❌ venv 디렉토리를 찾을 수 없습니다."
    echo "   먼저 'python3 -m venv venv' 명령으로 가상환경을 생성하세요."
    exit 1
fi

# 환경 변수 확인
echo "🔍 환경 변수 확인 중..."
python3 << 'PYEOF'
from config import Config

required = [
    ("SLACK_BOT_TOKEN", Config.SLACK_BOT_TOKEN),
    ("SLACK_APP_TOKEN", Config.SLACK_APP_TOKEN),
    ("SLACK_SIGNING_SECRET", Config.SLACK_SIGNING_SECRET),
    ("TENCENT_SECRET_ID", Config.TENCENT_SECRET_ID),
    ("TENCENT_SECRET_KEY", Config.TENCENT_SECRET_KEY),
]

missing = [name for name, value in required if not value]

if missing:
    print(f"❌ 다음 환경 변수가 설정되지 않았습니다: {', '.join(missing)}")
    print("   .env 파일을 확인하세요.")
    exit(1)
else:
    print("✅ 모든 필수 환경 변수가 설정되었습니다!")
PYEOF

if [ $? -ne 0 ]; then
    exit 1
fi

echo
echo "🚀 Bot 실행 중..."
echo "   중지하려면 Ctrl+C를 누르세요."
echo "=========================================="
echo

# Bot 실행
python3 app_v2.py
