#!/bin/bash

# StreamLive 입력 상태 확인 curl 테스트 스크립트
# 사용법: ./scripts/test-input-status.sh <CHANNEL_ID>

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 설정
API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"
CHANNEL_ID="${1:-}"

if [ -z "$CHANNEL_ID" ]; then
    echo -e "${RED}오류: 채널 ID가 필요합니다.${NC}"
    echo ""
    echo "사용법:"
    echo "  $0 <CHANNEL_ID>"
    echo ""
    echo "중요: CHANNEL_ID는 Tencent Cloud가 생성한 실제 채널 ID입니다."
    echo "      채널 이름이 아닙니다!"
    echo ""
    echo "채널 ID 확인 방법:"
    echo "  curl \"http://localhost:8000/api/v1/resources?service=StreamLive\" | jq '.resources[] | {id, name}'"
    echo ""
    echo "환경 변수:"
    echo "  API_BASE_URL - API 서버 주소 (기본값: http://localhost:8000)"
    echo ""
    echo "예제:"
    echo "  $0 694A308C79D37854B930"
    echo "  API_BASE_URL=http://api.example.com:8000 $0 694A308C79D37854B930"
    exit 1
fi

echo -e "${BLUE}=== StreamLive 입력 상태 확인 테스트 ===${NC}"
echo ""
echo -e "API 서버: ${GREEN}${API_BASE_URL}${NC}"
echo -e "채널 ID: ${GREEN}${CHANNEL_ID}${NC}"
echo ""

# 1. 채널 상세 정보 조회
echo -e "${YELLOW}[1/2] 채널 상세 정보 조회 중...${NC}"
CHANNEL_INFO=$(curl -s -X GET \
    "${API_BASE_URL}/api/v1/resources/${CHANNEL_ID}?service=StreamLive" \
    -H "Content-Type: application/json")

if [ $? -ne 0 ]; then
    echo -e "${RED}오류: API 서버에 연결할 수 없습니다.${NC}"
    echo "서버가 실행 중인지 확인하세요: curl ${API_BASE_URL}/api/v1/health"
    exit 1
fi

echo "$CHANNEL_INFO" | jq '.' 2>/dev/null || echo "$CHANNEL_INFO"
echo ""

# 2. 입력 상태 확인
echo -e "${YELLOW}[2/2] 입력 상태 확인 중...${NC}"
INPUT_STATUS=$(curl -s -X GET \
    "${API_BASE_URL}/api/v1/resources/${CHANNEL_ID}/input-status?service=StreamLive" \
    -H "Content-Type: application/json")

if [ $? -ne 0 ]; then
    echo -e "${RED}오류: 입력 상태 확인 실패${NC}"
    exit 1
fi

# 결과 출력
echo "$INPUT_STATUS" | jq '.' 2>/dev/null || echo "$INPUT_STATUS"
echo ""

# 결과 해석
ACTIVE_INPUT=$(echo "$INPUT_STATUS" | jq -r '.active_input // empty' 2>/dev/null)
if [ -n "$ACTIVE_INPUT" ]; then
    if [ "$ACTIVE_INPUT" = "main" ]; then
        echo -e "${GREEN}✓ Main 입력이 활성화되어 있습니다. (정상)${NC}"
    elif [ "$ACTIVE_INPUT" = "backup" ]; then
        echo -e "${YELLOW}⚠ Backup 입력이 활성화되어 있습니다. (Failover 발생)${NC}"
    else
        echo -e "${RED}✗ 입력 상태를 확인할 수 없습니다.${NC}"
    fi
else
    MESSAGE=$(echo "$INPUT_STATUS" | jq -r '.message // .error // "알 수 없는 오류"' 2>/dev/null)
    echo -e "${RED}✗ ${MESSAGE}${NC}"
fi

echo ""
echo -e "${BLUE}=== 테스트 완료 ===${NC}"
