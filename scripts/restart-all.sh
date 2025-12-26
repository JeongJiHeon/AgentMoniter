#!/bin/bash

# Agent Monitor - 모든 서버 재시작 스크립트
# Usage: ./scripts/restart-all.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Stopping all services..."
"$SCRIPT_DIR/stop-all.sh"

echo ""
echo "Waiting 2 seconds..."
sleep 2

echo ""
echo "Starting all services..."
"$SCRIPT_DIR/start-all.sh"

