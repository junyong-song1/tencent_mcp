#!/bin/bash
# MCP Server 테스트 스크립트

echo "🧪 MCP Server 테스트"
echo "===================="
echo ""

# 환경 변수 확인
if [ -z "$TENCENT_SECRET_ID" ] || [ -z "$TENCENT_SECRET_KEY" ]; then
    echo "❌ 환경 변수가 설정되지 않았습니다."
    echo "   .env 파일을 확인하거나 환경 변수를 설정하세요."
    exit 1
fi

echo "✅ 환경 변수 확인됨"
echo "   Region: ${TENCENT_REGION:-ap-seoul}"
echo ""

# Python 경로 확인
if ! command -v python &> /dev/null; then
    echo "❌ Python을 찾을 수 없습니다."
    exit 1
fi

echo "✅ Python 경로: $(which python)"
echo ""

# MCP 패키지 확인
echo "📦 MCP 패키지 확인 중..."
if ! python -c "import mcp" 2>/dev/null; then
    echo "⚠️  MCP 패키지가 설치되지 않았습니다."
    echo "   다음 명령어로 설치하세요:"
    echo "   pip install -r requirements.txt"
    exit 1
fi

echo "✅ MCP 패키지 확인됨"
echo ""

# 서버 모듈 확인
echo "🔍 MCP Server 모듈 확인 중..."
if ! python -c "from mcp_server import server" 2>/dev/null; then
    echo "❌ MCP Server 모듈을 찾을 수 없습니다."
    exit 1
fi

echo "✅ MCP Server 모듈 확인됨"
echo ""

echo "🚀 MCP Server를 시작합니다..."
echo "   (Ctrl+C로 종료)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 서버 실행 (stdio 모드)
python -m mcp_server
