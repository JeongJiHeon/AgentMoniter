# Agent Monitor

AI 에이전트를 안전하고 효율적으로 관리하고 모니터링하는 엔터프라이즈급 오케스트레이션 플랫폼입니다. **Human-in-the-Loop** 방식으로 AI 에이전트가 외부 서비스와 안전하게 상호작용할 수 있도록 지원합니다.

## 📋 목차

- [주요 기능](#-주요-기능)
- [기술 스택](#-기술-스택)
- [시작하기](#-시작하기)
- [환경 변수 설정](#-환경-변수-설정)
- [아키텍처](#-아키텍처)
- [사용 가이드](#-사용-가이드)
- [개발 가이드](#-개발-가이드)

## 🎯 주요 기능

### 1. 다중 에이전트 관리 시스템

- **에이전트 생성 및 구성**: 다양한 유형의 전문 에이전트 생성 (문서 처리, 이메일 처리, 리서치 등)
- **에이전트 라이프사이클 관리**: 생성, 시작, 일시정지, 재개, 중단
- **실시간 상태 모니터링**: 각 에이전트의 현재 상태, 작업 진행률, 통계 정보 실시간 확인
- **Thinking Mode State Machine**: 에이전트의 사고 과정을 4단계로 구조화 (`idle` → `exploring` → `structuring` → `validating` → `summarizing`)

### 2. 동적 워크플로우 오케스트레이션

- **자동 워크플로우 생성**: 사용자의 자연어 요청을 분석하여 최적의 워크플로우 자동 생성
- **다단계 작업 처리**: 복잡한 작업을 여러 에이전트가 순차/병렬로 처리
- **사용자 상호작용 지원**: 필요한 시점에 사용자에게 질문하고 입력 받기
- **Dynamic Orchestration**: 실시간으로 워크플로우를 동적으로 생성하고 실행

### 3. 승인 기반 워크플로우 (Human-in-the-Loop)

- **5가지 승인 유형 지원**:
  1. **Proceed**: 단순 승인/거부
  2. **Select Option**: 여러 옵션 중 선택
  3. **Provide Input**: 필수 정보 입력
  4. **Confirm Action**: 위험한 작업 확인
  5. **Review Result**: 결과 검토 및 승인
- **승인 큐 관리**: 모든 승인 요청을 중앙에서 관리
- **우선순위 기반 정렬**: 긴급한 승인 요청을 먼저 처리

### 4. MCP (Model Context Protocol) 서비스 통합

- **지원 서비스**: Notion, Gmail, Slack, Confluence
- **플러그인 아키텍처**: 새로운 서비스를 쉽게 추가 가능
- **자동 승인 정책**: 서비스별로 작업 유형에 따라 승인 필요 여부 자동 결정
- **롤백 지원**: 작업 실패 시 자동 롤백

### 5. 실시간 모니터링 및 대시보드

- **WebSocket 기반 실시간 상태 동기화**: 모든 상태 변경을 즉시 모든 클라이언트에 전송
- **에이전트 대시보드**: 모든 에이전트의 상태를 한눈에 확인
- **태스크 추적**: 각 태스크의 진행 상황, 관련 티켓, 승인 요청을 상세히 확인
- **통계 및 분석**: 에이전트별 작업 통계, 완료율, 성공률 등

### 6. Slack 통합 및 자동 태스크 생성

- **Slack 멘션 자동 감지**: 봇을 멘션하면 자동으로 태스크 생성
- **DM 지원**: 봇에게 직접 메시지를 보내면 태스크 생성
- **자동 할당**: Slack에서 생성된 태스크는 우선순위가 높게 설정되어 자동 할당

### 7. 개인화 및 온톨로지 관리

- **사용자 선호도 학습**: 대화를 통해 사용자의 선호도, 규칙, 금기사항 자동 추출
- **온톨로지 기반 검증**: 에이전트가 사용자 규칙을 위반하지 않도록 자동 검증
- **개인화 정보 저장**: 선호(preference), 사실(fact), 규칙(rule), 인사이트(insight) 등 체계적 관리

### 8. 태스크 관리 및 오케스트레이션

- **태스크 생성**: 수동 또는 자동(Slack 등)으로 태스크 생성
- **자동 할당**: LLM 기반으로 최적의 에이전트 자동 선택
- **수동 할당**: 사용자가 직접 에이전트 선택 가능
- **태스크 상세 보기**: 태스크별 티켓, 승인 요청, 진행 상황 상세 확인

## 🛠 기술 스택

### 프론트엔드
- **React 19** + **TypeScript**: 최신 React 기능 활용
- **Tailwind CSS**: 빠른 UI 개발
- **WebSocket**: 실시간 양방향 통신
- **Vite**: 빠른 개발 서버 및 빌드
- **Zustand**: 상태 관리
- **React Router**: 라우팅

### 백엔드
- **Python 3.9+**: 비동기 처리 중심
- **FastAPI**: 고성능 API 서버
- **WebSocket Server**: 실시간 통신 서버 (포트 8080)
- **Pydantic**: 타입 안전한 데이터 검증
- **Redis**: 상태 저장 및 캐싱

### 인프라
- **Docker Compose**: Redis 서비스 컨테이너화
- **ngrok**: 로컬 개발용 터널링 (Slack 웹훅)

### 통신 프로토콜
- **WebSocket (포트 8080)**: 실시간 이벤트 브로드캐스팅
- **HTTP/REST (포트 8000)**: Slack 웹훅 및 API 엔드포인트

### 외부 서비스 통합
- **MCP (Model Context Protocol)**: 표준화된 서비스 통합 인터페이스
- **OAuth2**: Gmail 등 인증 필요 서비스 지원

## 🚀 시작하기

### 사전 요구사항

- Node.js 18+ 및 npm
- Python 3.9+
- Redis (Docker Compose로 실행 가능)
- (선택) ngrok (Slack 통합 시)

### 빠른 시작

1. **저장소 클론**
```bash
git clone <repository-url>
cd agent-monitor_v2
```

2. **Redis 시작**
```bash
docker-compose up -d redis
```

또는 직접 설치:
```bash
redis-server
```

3. **백엔드 설정 및 실행**
```bash
cd server_python
pip install -r requirements.txt
cp .env.example .env  # 환경 변수 설정 (아래 참조)
python main.py
```

4. **프론트엔드 설정 및 실행**
```bash
# 루트 디렉토리에서
npm install
npm run dev
```

5. **스크립트를 사용한 전체 시작 (권장)**
```bash
./scripts/start-all.sh
```

서비스가 시작되면:
- **프론트엔드**: http://localhost:5173
- **백엔드 API**: http://localhost:8000
- **WebSocket**: ws://localhost:8080
- **Redis**: localhost:6379

### 서비스 관리 스크립트

```bash
# 모든 서비스 시작
./scripts/start-all.sh

# 모든 서비스 중지
./scripts/stop-all.sh

# 서비스 상태 확인
./scripts/status.sh

# 모든 서비스 재시작
./scripts/restart-all.sh
```

## ⚙️ 환경 변수 설정

`server_python/.env` 파일을 생성하고 다음 변수들을 설정하세요:

```bash
# WebSocket Server Port
WS_PORT=8080

# HTTP Server Port (Slack 웹훅용)
HTTP_PORT=8000

# Notion API Key
NOTION_API_KEY=your-notion-api-key

# Slack Configuration (선택사항)
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your-signing-secret
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# LLM 설정 (선택사항, 프론트엔드에서도 설정 가능)
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
```

### Slack 통합 설정

Slack 통합을 사용하려면 [SLACK_SETUP.md](server_python/SLACK_SETUP.md) 문서를 참조하세요.

## 🏗 아키텍처

### 디렉토리 구조

```
agent-monitor_v2/
├── src/                          # 프론트엔드 소스
│   ├── components/              # React 컴포넌트
│   │   ├── agents/             # 에이전트 관리 컴포넌트
│   │   ├── tasks/              # 태스크 관리 컴포넌트
│   │   ├── approval/           # 승인 큐 컴포넌트
│   │   ├── chat/               # 채팅 컴포넌트
│   │   ├── settings/           # 설정 컴포넌트
│   │   └── ...
│   ├── stores/                 # Zustand 상태 관리
│   ├── hooks/                  # React 커스텀 훅
│   ├── services/               # API 서비스
│   ├── errors/                 # 에러 처리 모듈
│   │   ├── ErrorBoundary.tsx  # React Error Boundary
│   │   ├── errorHandler.ts    # 에러 핸들러
│   │   └── types.ts           # 에러 타입 정의
│   ├── __tests__/              # 테스트 코드
│   └── types/                  # TypeScript 타입 정의
│
├── server_python/               # 백엔드 소스
│   ├── agents/                 # 에이전트 시스템
│   │   ├── base_agent.py      # 기본 에이전트 클래스
│   │   ├── generic_agent.py   # 범용 에이전트
│   │   ├── task_processor_agent.py  # 태스크 처리 에이전트
│   │   ├── dynamic_orchestration.py  # 동적 오케스트레이션
│   │   └── ...
│   ├── handlers/               # WebSocket 메시지 핸들러
│   │   ├── agent_handlers.py  # 에이전트 관련 핸들러
│   │   ├── approval_handlers.py  # 승인 요청 핸들러
│   │   ├── task_handlers.py   # 태스크 핸들러
│   │   ├── chat_handlers.py   # 채팅 핸들러
│   │   ├── config_handlers.py # 설정 핸들러
│   │   └── router.py          # 메시지 라우터
│   ├── startup/                # 서버 초기화 모듈
│   │   ├── agent_loader.py    # 에이전트 로딩
│   │   ├── mcp_initializer.py # MCP 서비스 초기화
│   │   └── server_config.py   # 서버 설정
│   ├── errors/                 # 에러 처리 모듈
│   │   ├── exceptions.py      # 커스텀 예외
│   │   ├── error_response.py  # 에러 응답
│   │   └── decorators.py      # 에러 핸들링 데코레이터
│   ├── mcp/                    # MCP 서비스
│   │   ├── base_mcp_service.py
│   │   ├── services/          # 개별 MCP 서비스 구현
│   │   └── ...
│   ├── models/                 # Pydantic 모델
│   ├── websocket/              # WebSocket 서버
│   ├── services/               # 비즈니스 로직 서비스
│   ├── tests/                  # 테스트 코드
│   │   ├── conftest.py        # pytest 공유 fixtures
│   │   └── unit/              # 단위 테스트
│   └── main.py                 # 메인 진입점
│
├── scripts/                     # 실행 스크립트
├── docker-compose.yml          # Docker Compose 설정
└── README.md                   # 이 문서
```

### 시스템 아키텍처

```
┌─────────────────┐
│   Frontend      │  React + TypeScript
│   (Vite)        │
└────────┬────────┘
         │ WebSocket (8080)
         │ HTTP (8000)
         │
┌────────▼──────────────────────┐
│   Backend Server              │
│   (FastAPI + WebSocket)       │
│                               │
│  ┌─────────────────────────┐ │
│  │  Agent Registry         │ │
│  │  - Agent Management     │ │
│  │  - Event Broadcasting   │ │
│  └─────────────────────────┘ │
│                               │
│  ┌─────────────────────────┐ │
│  │  Dynamic Orchestration  │ │
│  │  - Workflow Planning    │ │
│  │  - Multi-Agent Execution│ │
│  └─────────────────────────┘ │
│                               │
│  ┌─────────────────────────┐ │
│  │  MCP Services           │ │
│  │  - Notion, Gmail, Slack │ │
│  └─────────────────────────┘ │
└────────┬──────────────────────┘
         │
┌────────▼────────┐
│   Redis         │  상태 저장소
└─────────────────┘
```

### 데이터 흐름

1. **사용자 요청** → 프론트엔드에서 Task 생성
2. **오케스트레이션** → Dynamic Orchestration이 워크플로우 계획 수립
3. **에이전트 실행** → 여러 에이전트가 순차/병렬로 작업 수행
4. **승인 요청** → 외부 작업 시 사용자 승인 요청
5. **결과 반환** → WebSocket을 통해 실시간으로 상태 업데이트

## 📖 사용 가이드

### 1. 에이전트 생성

1. **Settings** 탭으로 이동
2. **Agents** 섹션에서 **Create Agent** 클릭
3. 에이전트 이름, 타입, 설명 입력
4. 생성된 에이전트는 **Dashboard**에서 확인 가능

### 2. 태스크 생성 및 할당

1. **Tasks** 탭으로 이동
2. **Create Task** 버튼 클릭
3. 태스크 제목과 설명 입력
4. **Assign Agent** 클릭하여 에이전트 할당 (자동 할당도 가능)
5. 에이전트가 작업을 시작하면 **Task Chat**에서 진행 상황 확인

### 3. 승인 요청 처리

1. **Approval Queue**에서 대기 중인 승인 요청 확인
2. 각 승인 요청의 상세 정보 확인
3. **Approve**, **Reject**, 또는 옵션 선택
4. 승인된 작업은 에이전트가 자동으로 실행

### 4. Slack 통합 사용

1. Slack에서 봇을 멘션하거나 DM 전송
2. 자동으로 태스크가 생성되어 Tasks 탭에 표시
3. 에이전트가 자동 할당되어 작업 시작

### 5. 실시간 모니터링

- **Dashboard**: 모든 에이전트의 상태와 통계 확인
- **Tasks**: 각 태스크의 진행 상황 상세 확인
- **Agent Activity Log**: 에이전트의 모든 활동 로그 확인

## 🔧 개발 가이드

### 백엔드 개발

```bash
cd server_python

# 의존성 설치
pip install -r requirements.txt

# 개발 서버 실행
python main.py

# 로그 확인
tail -f logs/backend.log
```

### 프론트엔드 개발

```bash
# 루트 디렉토리에서

# 의존성 설치
npm install

# 개발 서버 실행
npm run dev

# 빌드
npm run build

# 린트
npm run lint
```

### 테스트

```bash
# 백엔드 테스트 (pytest)
cd server_python
pip install -r requirements-dev.txt  # 테스트 의존성 설치
pytest                               # 전체 테스트 실행
pytest tests/unit/                   # 단위 테스트만 실행
pytest -v                            # 상세 출력

# 프론트엔드 테스트 (vitest)
npm run test                         # watch 모드로 테스트 실행
npm run test:run                     # 단일 실행
npm run test:coverage                # 커버리지 리포트 포함
```

### 새로운 MCP 서비스 추가

1. `server_python/mcp/services/` 디렉토리에 새 서비스 파일 생성
2. `BaseMCPService`를 상속받아 구현
3. `mcp_service_registry.py`에 서비스 등록
4. `main.py`에서 서비스 초기화

예시:
```python
from mcp.base_mcp_service import BaseMCPService

class MyCustomService(BaseMCPService):
    async def execute_action(self, action: str, params: dict):
        # 구현
        pass
```

## 🐛 문제 해결

### 서버가 시작되지 않는 경우

1. 포트가 이미 사용 중인지 확인:
```bash
lsof -i :8000  # HTTP 서버
lsof -i :8080  # WebSocket 서버
```

2. Redis가 실행 중인지 확인:
```bash
redis-cli ping
# 응답: PONG
```

3. 환경 변수가 올바르게 설정되었는지 확인

### WebSocket 연결이 안 되는 경우

1. 백엔드 서버가 실행 중인지 확인
2. 프론트엔드의 WebSocket URL이 올바른지 확인 (`ws://localhost:8080`)
3. 브라우저 콘솔에서 에러 메시지 확인

### Slack 웹훅이 작동하지 않는 경우

[server_python/SLACK_SETUP.md](server_python/SLACK_SETUP.md)의 문제 해결 섹션을 참조하세요.

## 📝 주요 개념

### Agent
작업을 수행하는 AI 에이전트. 각 에이전트는 고유한 ID, 이름, 타입, 설명을 가지며, 여러 작업을 동시에 처리할 수 있습니다.

### Task
사용자가 요청한 작업 단위. 하나의 태스크는 여러 에이전트에 의해 처리될 수 있으며, 워크플로우 형태로 실행됩니다.

### Ticket
에이전트가 생성하는 작업 단위. 승인이 필요한 작업은 Ticket으로 생성되어 사용자 승인을 기다립니다.

### Approval Request
외부 서비스 작업 수행 전 사용자 승인이 필요한 경우 생성되는 요청. 5가지 타입이 있습니다.

### Workflow
여러 에이전트가 협업하여 하나의 태스크를 처리하는 과정. Dynamic Orchestration이 자동으로 워크플로우를 생성합니다.

## 🔮 향후 계획

### 단기 (1-3개월)
- [ ] 추가 MCP 서비스 통합 (Jira, GitHub 등)
- [ ] 에이전트 성능 분석 대시보드
- [ ] 워크플로우 템플릿 라이브러리

### 중기 (3-6개월)
- [ ] Knowledge Base 구축 및 임베딩
- [ ] 에이전트 간 협업 최적화
- [ ] 모바일 앱 지원

### 장기 (6개월+)
- [ ] 멀티 테넌트 지원
- [ ] 에이전트 마켓플레이스
- [ ] AI 모델 파인튜닝 지원

## 📄 라이선스

(라이선스 정보 추가)

## 🤝 기여

(기여 가이드 추가)

---

**Agent Monitor** - 안전하고 스마트한 AI 자동화 플랫폼
