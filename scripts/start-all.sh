#!/bin/bash

# Agent Monitor - 모든 서버 시작 스크립트
# Usage: ./scripts/start-all.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
PID_DIR="$PROJECT_DIR/.pids"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 디렉토리 생성
mkdir -p "$LOG_DIR"
mkdir -p "$PID_DIR"

echo -e "${BLUE}=================================================${NC}"
echo -e "${BLUE}  Agent Monitor - Starting All Services${NC}"
echo -e "${BLUE}=================================================${NC}"
echo ""

# 1. Redis 시작
echo -e "${YELLOW}[1/5] Starting Redis...${NC}"
if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}  ✓ Redis already running${NC}"
else
    redis-server --daemonize yes --logfile "$LOG_DIR/redis.log"
    sleep 1
    if redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}  ✓ Redis started on port 6379${NC}"
    else
        echo -e "${RED}  ✗ Failed to start Redis${NC}"
        exit 1
    fi
fi

# 2. Backend (Python FastAPI) 시작
echo -e "${YELLOW}[2/5] Starting Backend Server...${NC}"
if lsof -i :8000 > /dev/null 2>&1; then
    echo -e "${GREEN}  ✓ Backend already running on port 8000${NC}"
else
    cd "$PROJECT_DIR/server_python"
    nohup python main.py > "$LOG_DIR/backend.log" 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > "$PID_DIR/backend.pid"
    sleep 4  # Backend 시작에 더 많은 시간 필요
    if lsof -i :8000 > /dev/null 2>&1; then
        echo -e "${GREEN}  ✓ Backend started on port 8000 (PID: $BACKEND_PID)${NC}"
    else
        echo -e "${RED}  ✗ Failed to start Backend${NC}"
        cat "$LOG_DIR/backend.log" | tail -20
        exit 1
    fi
fi

# 3. WebSocket 서버 확인 (Backend에 포함)
echo -e "${YELLOW}[3/5] Checking WebSocket Server...${NC}"
sleep 1
if lsof -i :8080 > /dev/null 2>&1; then
    echo -e "${GREEN}  ✓ WebSocket running on port 8080${NC}"
else
    echo -e "${YELLOW}  ⏳ WebSocket starting with backend...${NC}"
fi

# 4. Frontend (Vite) 시작
echo -e "${YELLOW}[4/5] Starting Frontend Server...${NC}"
FRONTEND_PORT=""
for port in 5173 5174 5175 5176 5177 5178 5179 5180; do
    if lsof -i :$port > /dev/null 2>&1; then
        FRONTEND_PORT=$port
        break
    fi
done

if [ -n "$FRONTEND_PORT" ]; then
    echo -e "${GREEN}  ✓ Frontend already running on port $FRONTEND_PORT${NC}"
else
    cd "$PROJECT_DIR"
    nohup npm run dev > "$LOG_DIR/frontend.log" 2>&1 &
    FRONTEND_PID=$!
    echo $FRONTEND_PID > "$PID_DIR/frontend.pid"
    sleep 3
    # 포트 찾기
    for port in 5173 5174 5175 5176 5177 5178 5179 5180; do
        if lsof -i :$port > /dev/null 2>&1; then
            FRONTEND_PORT=$port
            break
        fi
    done
    if [ -n "$FRONTEND_PORT" ]; then
        echo -e "${GREEN}  ✓ Frontend started on port $FRONTEND_PORT (PID: $FRONTEND_PID)${NC}"
    else
        echo -e "${RED}  ✗ Failed to start Frontend${NC}"
        cat "$LOG_DIR/frontend.log" | tail -20
        exit 1
    fi
fi

# 5. ngrok 시작
echo -e "${YELLOW}[5/5] Starting ngrok...${NC}"
if curl -s http://localhost:4040/api/tunnels > /dev/null 2>&1; then
    echo -e "${GREEN}  ✓ ngrok already running${NC}"
    NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | grep -o '"public_url":"https[^"]*"' | head -1 | cut -d'"' -f4)
    if [ -n "$NGROK_URL" ]; then
        echo -e "${GREEN}    URL: $NGROK_URL${NC}"
    fi
else
    nohup ngrok http 8000 > "$LOG_DIR/ngrok.log" 2>&1 &
    NGROK_PID=$!
    echo $NGROK_PID > "$PID_DIR/ngrok.pid"
    sleep 3
    if curl -s http://localhost:4040/api/tunnels > /dev/null 2>&1; then
        NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | grep -o '"public_url":"https[^"]*"' | head -1 | cut -d'"' -f4)
        echo -e "${GREEN}  ✓ ngrok started (PID: $NGROK_PID)${NC}"
        if [ -n "$NGROK_URL" ]; then
            echo -e "${GREEN}    URL: $NGROK_URL${NC}"
        else
            echo -e "${YELLOW}    URL: Check http://localhost:4040${NC}"
        fi
    else
        echo -e "${RED}  ✗ Failed to start ngrok${NC}"
    fi
fi

echo ""
echo -e "${BLUE}=================================================${NC}"
echo -e "${GREEN}  All Services Started!${NC}"
echo -e "${BLUE}=================================================${NC}"
echo ""
echo -e "  ${BLUE}Redis:${NC}      localhost:6379"
echo -e "  ${BLUE}Backend:${NC}    http://localhost:8000"
echo -e "  ${BLUE}WebSocket:${NC}  ws://localhost:8080"
echo -e "  ${BLUE}Frontend:${NC}   http://localhost:${FRONTEND_PORT:-5173}"
echo -e "  ${BLUE}ngrok:${NC}      http://localhost:4040 (Dashboard)"
echo ""
echo -e "  ${YELLOW}Logs:${NC} $LOG_DIR/"
echo -e "  ${YELLOW}Stop:${NC} ./scripts/stop-all.sh"
echo ""

