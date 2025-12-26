#!/bin/bash

# Agent Monitor - 서버 상태 확인 스크립트
# Usage: ./scripts/status.sh

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=================================================${NC}"
echo -e "${BLUE}  Agent Monitor - Service Status${NC}"
echo -e "${BLUE}=================================================${NC}"
echo ""

# Redis
echo -e -n "  ${BLUE}Redis:${NC}      "
if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}● Running${NC} (localhost:6379)"
else
    echo -e "${RED}○ Stopped${NC}"
fi

# Backend
echo -e -n "  ${BLUE}Backend:${NC}    "
if lsof -i :8000 > /dev/null 2>&1; then
    PID=$(lsof -t -i :8000 2>/dev/null | head -1)
    echo -e "${GREEN}● Running${NC} (http://localhost:8000, PID: $PID)"
else
    echo -e "${RED}○ Stopped${NC}"
fi

# WebSocket
echo -e -n "  ${BLUE}WebSocket:${NC}  "
if lsof -i :8080 > /dev/null 2>&1; then
    PID=$(lsof -t -i :8080 2>/dev/null | head -1)
    echo -e "${GREEN}● Running${NC} (ws://localhost:8080, PID: $PID)"
else
    echo -e "${RED}○ Stopped${NC}"
fi

# Frontend
echo -e -n "  ${BLUE}Frontend:${NC}   "
FRONTEND_PORT=""
for port in 5173 5174 5175 5176 5177 5178 5179 5180; do
    if lsof -i :$port > /dev/null 2>&1; then
        FRONTEND_PORT=$port
        break
    fi
done
if [ -n "$FRONTEND_PORT" ]; then
    PID=$(lsof -t -i :$FRONTEND_PORT 2>/dev/null | head -1)
    echo -e "${GREEN}● Running${NC} (http://localhost:$FRONTEND_PORT, PID: $PID)"
else
    echo -e "${RED}○ Stopped${NC}"
fi

# ngrok
echo -e -n "  ${BLUE}ngrok:${NC}      "
if curl -s http://localhost:4040/api/tunnels > /dev/null 2>&1; then
    NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null | grep -o '"public_url":"https[^"]*"' | head -1 | cut -d'"' -f4)
    if [ -n "$NGROK_URL" ]; then
        echo -e "${GREEN}● Running${NC} ($NGROK_URL)"
    else
        echo -e "${GREEN}● Running${NC} (Dashboard: http://localhost:4040)"
    fi
else
    echo -e "${RED}○ Stopped${NC}"
fi

echo ""
echo -e "${BLUE}=================================================${NC}"
echo ""

