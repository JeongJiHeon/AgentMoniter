# Agent Monitor 백엔드 분석 및 Python 변환 문서

## 프로젝트 개요

Agent Monitor는 AI 에이전트를 모니터링하고 관리하는 시스템입니다. 원래 TypeScript/Node.js로 작성되었으며, 이를 Python으로 완전히 변환했습니다.

## 주요 구성 요소

### 1. 모델 (Models)
- **Agent**: 에이전트 상태, 사고 모드, 제약조건, 권한 등
- **Ticket**: 작업 단위, 승인 요청, 실행 계획 등
- **Approval**: 승인 요청 및 응답 처리
- **Ontology**: 사용자 사고 규칙, 금기 사항, 승인 규칙 등
- **WebSocket**: 실시간 통신 메시지 타입

### 2. Agent 시스템
- **BaseAgent**: 모든 에이전트의 기본 추상 클래스
  - 탐색(explore) → 구조화(structure) → 검증(validate) → 요약(summarize) 파이프라인
  - 상태 머신을 통한 사고 모드 관리
  - 이벤트 시스템
  
- **AgentRegistry**: 에이전트 인스턴스 관리
  - 에이전트 생성/등록/해제
  - 전역 이벤트 브로드캐스트
  - 상태 조회 및 통계

- **ThinkingModeStateMachine**: 사고 모드 상태 머신
  - idle → exploring → structuring → validating → summarizing → idle
  - 상태 전환 규칙 및 히스토리 관리

### 3. MCP 서비스 (Model Context Protocol)
- **BaseMCPService**: MCP 서비스 기본 클래스
  - 읽기 작업: 승인 불필요
  - 쓰기 작업: 승인 필요
  - 전송 작업: 승인 필수
  
- **MCPServiceRegistry**: MCP 서비스 관리
  - 서비스 등록/연결/해제
  - 작업 실행 및 검증

- **구현된 서비스**:
  - NotionService: Notion 페이지 관리
  - GmailService: 이메일 읽기/초안 생성
  - SlackService: Slack 메시지 관리
  - ConfluenceService: Confluence 페이지 관리

### 4. WebSocket 서버
- **AgentMonitorWebSocketServer**: 실시간 통신 서버
  - 클라이언트 연결 관리
  - Heartbeat 체크
  - 브로드캐스트 메시지 전송
  - 클라이언트 액션 처리

## TypeScript → Python 변환 매핑

| TypeScript | Python |
|------------|--------|
| Zod | Pydantic |
| async/await | asyncio |
| ws (WebSocket) | websockets |
| uuid | uuid (표준 라이브러리) |
| Map | dict |
| Set | set |
| interface | Protocol/ABC |
| class extends | ABC 상속 |
| enum | Enum |

## 주요 변경 사항

1. **타입 시스템**: Zod → Pydantic
   - 스키마 정의를 Pydantic 모델로 변환
   - 런타임 검증 및 직렬화 지원

2. **비동기 처리**: Node.js Promise → Python asyncio
   - 모든 비동기 함수를 async/await로 변환
   - asyncio.gather를 사용한 병렬 처리

3. **이벤트 시스템**: TypeScript EventEmitter → Python 콜백
   - 핸들러를 dict/set으로 관리
   - emit 메서드로 이벤트 발생

4. **WebSocket**: ws → websockets
   - websockets 라이브러리 사용
   - 비동기 연결 처리

## 실행 방법

```bash
# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정 (.env 파일 생성)
cp .env.example .env

# 서버 실행
python main.py
```

## 환경 변수

- `WS_PORT`: WebSocket 서버 포트 (기본값: 8080)
- `NOTION_API_KEY`: Notion API 키
- `GMAIL_CLIENT_ID`: Gmail 클라이언트 ID
- `GMAIL_CLIENT_SECRET`: Gmail 클라이언트 시크릿
- `SLACK_BOT_TOKEN`: Slack 봇 토큰
- `CONFLUENCE_URL`: Confluence URL
- `CONFLUENCE_USERNAME`: Confluence 사용자명
- `CONFLUENCE_API_TOKEN`: Confluence API 토큰

## 아키텍처 특징

1. **승인 기반 작업 처리**: 모든 중요한 작업은 사용자 승인 필요
2. **온톨로지 기반 제약**: 사용자 규칙에 따른 자동 제약 적용
3. **상태 머신**: 명확한 상태 전환 규칙
4. **이벤트 기반**: 느슨한 결합을 위한 이벤트 시스템
5. **실시간 모니터링**: WebSocket을 통한 실시간 상태 업데이트

## 향후 개선 사항

1. 실제 API 연동 구현 (현재는 모의 구현)
2. 데이터베이스 연동 (에이전트/티켓 영구 저장)
3. 인증/인가 시스템
4. 로깅 시스템 개선
5. 에러 처리 강화
6. 단위 테스트 추가

