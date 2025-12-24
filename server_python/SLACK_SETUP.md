# Slack 연동 설정 가이드

## 1. Slack App 생성

1. [Slack API](https://api.slack.com/apps)에 접속
2. "Create New App" 클릭
3. "From scratch" 선택
4. App 이름과 워크스페이스 선택

## 2. Event Subscriptions 설정

1. 좌측 메뉴에서 "Event Subscriptions" 선택
2. "Enable Events" 토글 활성화
3. Request URL 입력: 
   - 로컬 개발: ngrok 등을 사용하여 외부 URL 생성
   - 예: `https://your-ngrok-url.ngrok.io/api/slack/webhook`
   - **중요**: ngrok URL은 `/api/slack/webhook` 경로를 포함해야 합니다
4. URL을 입력하면 Slack이 자동으로 `challenge` 파라미터를 보내고, 서버가 이를 반환해야 합니다
5. Subscribe to bot events에 다음 이벤트 추가:
   - `app_mention` - 봇이 멘션된 경우
   - `message.im` - DM을 받은 경우
   - `message.channels` - 채널 메시지 (선택사항)

## 3. Bot Token 및 Signing Secret

1. 좌측 메뉴에서 "OAuth & Permissions" 선택
2. "Bot Token Scopes"에 다음 권한 추가:
   - `app_mentions:read`
   - `channels:read`
   - `chat:write`
   - `im:read`
   - `im:write`
3. "Install App to Workspace" 클릭하여 워크스페이스에 설치
4. "Bot User OAuth Token" 복사 (xoxb-로 시작)
5. 좌측 메뉴에서 "Basic Information" 선택
6. "Signing Secret" 복사

## 4. 환경 변수 설정

`.env` 파일에 다음을 추가:

```bash
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_SIGNING_SECRET=your-signing-secret-here
HTTP_PORT=8000
```

## 5. 서버 실행

```bash
python main.py
```

서버가 실행되면:
- WebSocket: `ws://localhost:8080`
- HTTP API: `http://localhost:8000`
- Slack Webhook: `http://localhost:8000/api/slack/webhook`

## 6. 로컬 개발 시 ngrok 사용

```bash
# ngrok 설치 후
ngrok http 8000

# 생성된 URL을 Slack Event Subscriptions의 Request URL에 입력
# 예: https://abc123.ngrok.io/api/slack/webhook
```

## 동작 방식

1. Slack에서 봇을 멘션하거나 DM을 보내면
2. Slack이 웹훅으로 이벤트 전송
3. 서버가 이벤트를 받아서 Task로 변환
4. WebSocket을 통해 프론트엔드에 브로드캐스트
5. Tasks 탭에 자동으로 표시됨

