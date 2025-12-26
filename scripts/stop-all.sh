#!/bin/bash

# Agent Monitor - 모든 서버 종료 스크립트
# Usage: ./scripts/stop-all.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PID_DIR="$PROJECT_DIR/.pids"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=================================================${NC}"
echo -e "${BLUE}  Agent Monitor - Stopping All Services${NC}"
echo -e "${BLUE}=================================================${NC}"
echo ""

# 1. ngrok 종료
echo -e "${YELLOW}[1/5] Stopping ngrok...${NC}"
if pgrep -f "ngrok" > /dev/null; then
    pkill -f "ngrok" 2>/dev/null
    sleep 1
    echo -e "${GREEN}  ✓ ngrok stopped${NC}"
else
    echo -e "${YELLOW}  - ngrok not running${NC}"
fi

# 2. Frontend 종료
echo -e "${YELLOW}[2/5] Stopping Frontend...${NC}"
FRONTEND_STOPPED=false
for port in 5173 5174 5175 5176 5177 5178 5179 5180; do
    PID=$(lsof -t -i :$port 2>/dev/null)
    if [ -n "$PID" ]; then
        kill -9 $PID 2>/dev/null
        FRONTEND_STOPPED=true
        echo -e "${GREEN}  ✓ Frontend stopped (port $port)${NC}"
    fi
done
if [ "$FRONTEND_STOPPED" = false ]; then
    echo -e "${YELLOW}  - Frontend not running${NC}"
fi

# 3. Backend & WebSocket 종료
echo -e "${YELLOW}[3/5] Stopping Backend & WebSocket...${NC}"
BACKEND_PID=$(lsof -t -i :8000 2>/dev/null)
WS_PID=$(lsof -t -i :8080 2>/dev/null)

if [ -n "$BACKEND_PID" ]; then
    kill -9 $BACKEND_PID 2>/dev/null
    echo -e "${GREEN}  ✓ Backend stopped (port 8000)${NC}"
else
    echo -e "${YELLOW}  - Backend not running${NC}"
fi

if [ -n "$WS_PID" ]; then
    kill -9 $WS_PID 2>/dev/null
    echo -e "${GREEN}  ✓ WebSocket stopped (port 8080)${NC}"
else
    echo -e "${YELLOW}  - WebSocket not running${NC}"
fi

# 4. Redis 종료
echo -e "${YELLOW}[4/5] Stopping Redis...${NC}"
if redis-cli ping > /dev/null 2>&1; then
    redis-cli shutdown 2>/dev/null || pkill -f "redis-server" 2>/dev/null
    sleep 1
    echo -e "${GREEN}  ✓ Redis stopped${NC}"
else
    echo -e "${YELLOW}  - Redis not running${NC}"
fi

# 5. PID 파일 정리
echo -e "${YELLOW}[5/5] Cleaning up...${NC}"
rm -f "$PID_DIR"/*.pid 2>/dev/null
echo -e "${GREEN}  ✓ PID files cleaned${NC}"

echo ""
echo -e "${BLUE}=================================================${NC}"
echo -e "${GREEN}  All Services Stopped!${NC}"
echo -e "${BLUE}=================================================${NC}"
echo ""

