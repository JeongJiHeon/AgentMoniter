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

## 문제 해결

### DM 메시지가 오지 않는 경우

1. **Slack Event Subscriptions 확인**
   - [Slack API](https://api.slack.com/apps) → 해당 앱 선택
   - "Event Subscriptions" 메뉴로 이동
   - "Enable Events" 토글이 **활성화**되어 있는지 확인
   - "Request URL"이 올바른지 확인 (예: `https://your-ngrok-url.ngrok.io/api/slack/webhook`)
   - Request URL 옆에 "Verified" 표시가 있는지 확인

2. **Bot Events 구독 확인**
   - "Subscribe to bot events" 섹션에서 다음 이벤트가 추가되어 있는지 확인:
     - ✅ `app_mention` - 봇 멘션
     - ✅ `message.im` - **DM 메시지 (필수!)**
     - (선택) `message.channels` - 채널 메시지

3. **ngrok URL 확인 (로컬 개발 시)**
   ```bash
   # ngrok이 실행 중인지 확인
   # ngrok URL이 변경되었는지 확인
   # Slack Event Subscriptions의 Request URL을 최신 ngrok URL로 업데이트
   ```

4. **서버 로그 확인**
   ```bash
   # backend.log 파일에서 Slack 웹훅 요청 확인
   tail -f logs/backend.log | grep SlackWebhook
   
   # 또는 서버 콘솔에서 확인
   # DM을 보낼 때 다음과 같은 로그가 나타나야 함:
   # [SlackWebhook] New request received
   # [SlackWebhookService] Detected message event
   # [SlackWebhookService] Detected DM
   ```

5. **웹훅 엔드포인트 테스트**
   ```bash
   # 로컬 서버가 실행 중일 때
   curl -X POST http://localhost:8000/api/slack/webhook \
     -H "Content-Type: application/json" \
     -d '{"type":"url_verification","challenge":"test123"}'
   
   # 응답: {"challenge":"test123"} 이 나와야 함
   ```

6. **Slack 앱 설치 확인**
   - "OAuth & Permissions" 메뉴에서
   - "Install App to Workspace" 버튼을 클릭하여 워크스페이스에 설치되어 있는지 확인
   - "Reinstall App"이 보이면 이미 설치된 것

7. **봇과의 DM 채널 확인**
   - Slack에서 봇과 DM을 시작할 때
   - 봇이 처음으로 메시지를 보낼 수 있어야 함
   - 또는 봇을 채널에 초대한 후 DM을 시도

### 웹훅 요청이 전혀 오지 않는 경우

1. **ngrok URL 만료 확인**
   - ngrok 무료 버전은 URL이 자주 변경됨
   - 새로운 ngrok URL을 Slack Event Subscriptions에 업데이트

2. **방화벽/네트워크 확인**
   - 서버가 인터넷에 접근 가능한지 확인
   - ngrok이 정상 작동하는지 확인: `curl https://your-ngrok-url.ngrok.io/api/slack/webhook`

3. **Slack 앱 상태 확인**
   - Slack API 대시보드에서 앱이 활성화되어 있는지 확인
   - 워크스페이스에서 앱이 제거되지 않았는지 확인

4. **서버 재시작**
   ```bash
   # 서버를 재시작하여 최신 설정 적용
   python main.py
   ```

### 디버깅 팁

- 서버 로그에서 `[SlackWebhook]`로 시작하는 모든 로그를 확인
- Slack에서 DM을 보낼 때 실시간으로 로그 확인
- Slack Event Subscriptions 페이지에서 "Recent Events" 탭 확인하여 이벤트가 전송되는지 확인

