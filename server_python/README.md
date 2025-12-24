# Agent Monitor Server (Python)

Python으로 구현된 Agent Monitor 백엔드 서버입니다.

## 설치

```bash
pip install -r requirements.txt
```

## 환경 변수 설정

`.env` 파일을 생성하고 다음 변수들을 설정하세요:

```bash
# WebSocket Server Port
WS_PORT=8080

# HTTP Server Port (Slack 웹훅용)
HTTP_PORT=8000

# Notion API Key
NOTION_API_KEY=demo-key

# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your-signing-secret
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

## 실행

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8080
```

또는

```bash
python main.py
```

## 구조

- `models/` - Pydantic 모델 정의
- `agents/` - Agent 시스템 구현
- `mcp/` - MCP 서비스 구현
- `websocket/` - WebSocket 서버 구현
- `main.py` - 메인 진입점

