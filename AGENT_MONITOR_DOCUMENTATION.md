# Agent Monitor - Technical Documentation

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Project Structure](#3-project-structure)
4. [Core Components](#4-core-components)
5. [Data Flow](#5-data-flow)
6. [Key Features](#6-key-features)
7. [Setup and Configuration](#7-setup-and-configuration)
8. [API Documentation](#8-api-documentation)
9. [Extending the System](#9-extending-the-system)
10. [Troubleshooting](#10-troubleshooting)

---

## 1. Overview

### 1.1 Project Introduction

Agent Monitor is an AI agent orchestration and monitoring system that manages autonomous agents with human oversight. The system enforces a human-in-the-loop approval workflow for sensitive operations while allowing agents to operate autonomously for routine tasks.

### 1.2 Purpose

The system addresses the challenge of deploying AI agents in production environments where:
- Agents need to access external services (Slack, Gmail, Notion, Confluence)
- Operations require user approval before execution
- Agent behavior must follow user-defined rules and constraints
- Real-time monitoring and intervention capabilities are essential
- Task assignment can be automated or manual based on context

### 1.3 Key Features

- **Multi-Agent Management**: Create, configure, and monitor multiple AI agents simultaneously
- **Task Orchestration**: Intelligent task assignment with both automatic and manual modes
- **Task Detail View**: Track task progress with detailed view showing tickets and approval requests
- **Approval Workflow**: Tiered approval system for agent operations based on risk level
- **MCP Service Integration**: Plugin architecture for external service integrations (Slack, Gmail, Notion, Confluence)
- **Real-time Communication**: WebSocket-based live updates between frontend and backend
- **Data Persistence**: Automatic save/load of settings, tasks, and customizations using localStorage
- **Ontology-based Constraints**: User-defined rules, taboos, and preferences enforced on agents
- **Thinking Mode State Machine**: Transparent agent reasoning process (explore → structure → validate → summarize)
- **Slack Integration**: Automatic task creation from Slack mentions and direct messages
- **Personalization**: User preference learning and context awareness

---

## 2. Architecture

### 2.1 System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React + TypeScript)           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  Task Panel  │  │ Agent Panel  │  │   Settings   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Approval UI  │  │  Chat Panel  │  │ Tickets View │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                            │
                   WebSocket (port 8080)
                            │
┌─────────────────────────────────────────────────────────────────┐
│                  Backend (Python + FastAPI)                      │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │               WebSocket Server                              │ │
│  │  - Client connection management                             │ │
│  │  - Real-time event broadcasting                             │ │
│  │  - Heartbeat monitoring                                     │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │               Agent Registry                                 │ │
│  │  - Agent lifecycle management                               │ │
│  │  - Event coordination                                        │ │
│  │  - State synchronization                                     │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │               MCP Service Registry                          │ │
│  │  - Service registration                                      │ │
│  │  - Operation execution                                       │ │
│  │  - Approval validation                                       │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │            Slack Webhook Service (HTTP)                     │ │
│  │  - Event receiving (port 8000)                              │ │
│  │  - Task creation from Slack                                 │ │
│  │  - Signature verification                                    │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                            │
                     External Services
                            │
    ┌───────────┬───────────┼───────────┬────────────┐
    │           │           │           │            │
┌───▼───┐  ┌───▼────┐  ┌──▼────┐  ┌──▼──────┐  ┌──▼────┐
│ Slack │  │ Gmail  │  │ Notion│  │Confluence│  │  LLM  │
└───────┘  └────────┘  └───────┘  └──────────┘  └───────┘
```

### 2.2 Technology Stack

#### Frontend
- **Framework**: React 19.2.0 with TypeScript
- **Build Tool**: Vite 7.2.4
- **Styling**: Tailwind CSS 4.1.18
- **State Management**: React hooks (useState, useEffect, useCallback)
- **Real-time Communication**: WebSocket API

#### Backend
- **Runtime**: Python 3.9+
- **Web Framework**: FastAPI 0.115.0
- **ASGI Server**: Uvicorn 0.32.0
- **WebSocket**: websockets 13.1
- **Data Validation**: Pydantic 2.9.2
- **Environment Config**: python-dotenv 1.0.1
- **HTTP Client**: aiohttp 3.11.3

#### Communication Protocols
- **WebSocket**: Real-time bidirectional communication (port 8080)
- **HTTP/REST**: Slack webhook endpoint (port 8000)

---

## 3. Project Structure

### 3.1 Directory Overview

```
agent-monitor_v2/
├── src/                          # Frontend React application
│   ├── components/               # React components
│   │   ├── agents/              # Agent-related components
│   │   ├── approval/            # Approval queue UI
│   │   ├── chat/                # Chat interface
│   │   ├── layout/              # Layout components
│   │   ├── personalization/     # Personalization panel
│   │   ├── settings/            # Settings UI
│   │   ├── tasks/               # Task management UI
│   │   │   ├── TaskPanel.tsx   # Main task panel with filtering
│   │   │   ├── TaskCard.tsx    # Individual task card component
│   │   │   ├── TaskDetailModal.tsx  # Task detail view modal
│   │   │   ├── CreateTaskModal.tsx  # Task creation modal
│   │   │   └── AssignAgentModal.tsx # Agent assignment modal
│   │   └── tickets/             # Ticket display
│   ├── hooks/                   # Custom React hooks
│   │   └── useWebSocket.ts      # WebSocket connection hook
│   ├── services/                # Business logic services
│   │   └── orchestration.ts     # Task-to-agent assignment
│   ├── types/                   # TypeScript type definitions
│   ├── utils/                   # Utility functions
│   │   └── localStorage.ts      # localStorage persistence utility
│   └── App.tsx                  # Main application component
│
├── server_python/               # Backend Python application
│   ├── agents/                  # Agent system implementation
│   │   ├── base_agent.py        # Abstract base agent class
│   │   ├── agent_registry.py    # Agent lifecycle manager
│   │   ├── thinking_mode_state_machine.py  # State transitions
│   │   └── types.py             # Agent type definitions
│   │
│   ├── mcp/                     # Model Context Protocol services
│   │   ├── base_mcp_service.py  # Abstract MCP service
│   │   ├── mcp_service_registry.py  # Service manager
│   │   ├── types.py             # MCP type definitions
│   │   └── services/            # Concrete service implementations
│   │       ├── confluence_service.py
│   │       ├── gmail_service.py
│   │       ├── notion_service.py
│   │       └── slack_service.py
│   │
│   ├── models/                  # Pydantic data models
│   │   ├── agent.py             # Agent state model
│   │   ├── approval.py          # Approval request model
│   │   ├── ontology.py          # User rules and preferences
│   │   ├── task.py              # Task model
│   │   ├── ticket.py            # Ticket model
│   │   └── websocket.py         # WebSocket message types
│   │
│   ├── websocket/               # WebSocket server
│   │   └── websocket_server.py  # Connection and message handling
│   │
│   ├── services/                # Business logic services
│   │   └── slack_webhook.py     # Slack event processing
│   │
│   ├── api/                     # HTTP API routes
│   │   └── slack_webhook.py     # Slack webhook endpoint
│   │
│   ├── main.py                  # Application entry point
│   ├── requirements.txt         # Python dependencies
│   └── .env                     # Environment configuration
│
├── public/                      # Static assets
├── dist/                        # Production build output
├── package.json                 # Node.js dependencies
├── vite.config.ts              # Vite configuration
├── tailwind.config.js          # Tailwind CSS configuration
└── tsconfig.json               # TypeScript configuration
```

### 3.2 Key Configuration Files

| File | Purpose |
|------|---------|
| `package.json` | Frontend dependencies and npm scripts |
| `vite.config.ts` | Development server and build configuration |
| `tsconfig.json` | TypeScript compiler settings |
| `tailwind.config.js` | CSS utility classes configuration |
| `requirements.txt` | Python backend dependencies |
| `.env` | Environment variables (ports, API keys) |
| `server_python/main.py` | Backend server initialization |

---

## 4. Core Components

### 4.1 Frontend Components (React)

#### 4.1.1 App.tsx - Main Application

Central application state management and routing.

**Key Responsibilities:**
- WebSocket connection lifecycle
- Global state management (agents, tasks, tickets, approvals)
- Task auto-assignment orchestration
- Event handler coordination

**Critical State:**
```typescript
const [tasks, setTasks] = useState<Task[]>([]);
const [agents, setAgents] = useState<Agent[]>([]);
const [tickets, setTickets] = useState<Ticket[]>([]);
const [approvalQueue, setApprovalQueue] = useState<ApprovalRequest[]>([]);
const [autoAssignMode, setAutoAssignMode] = useState<'global' | 'manual'>('manual');
```

**Auto-Assignment Logic:**
- **Global Mode**: All tasks auto-assigned unless explicitly disabled (`autoAssign: false`)
- **Manual Mode**: Only tasks with `autoAssign: true` or meeting default criteria
- **Default Criteria**: High/urgent priority OR Slack-sourced tasks

#### 4.1.2 TaskPanel Component

Task creation, display, and management interface.

**Features:**
- Create tasks with priority, tags, and due dates
- Assign tasks to agents manually or automatically
- Filter and sort tasks by status, priority, source
- Analyze Slack/MCP messages to extract tasks using LLM
- Toggle between global and manual auto-assignment modes

#### 4.1.3 AgentPanel Component

Displays active agents and their current state.

**Agent Card Information:**
- Name, type, and status
- Current thinking mode (idle, exploring, structuring, validating, summarizing)
- Active task description
- Constraints and permissions

#### 4.1.4 ApprovalQueue Component

User approval interface for agent-requested operations.

**Approval Types:**
- **Proceed**: Simple approve/reject
- **Select Option**: Choose from multiple alternatives
- **Provide Input**: Fill required fields
- **Confirm Action**: Verify before execution
- **Review Result**: Validate agent output

#### 4.1.5 ChatPanel Component

LLM-powered chat interface for system interaction.

**Capabilities:**
- Generate custom agents using natural language
- Extract insights for personalization
- Query system state
- Get recommendations

### 4.2 Backend Models (Python)

#### 4.2.1 Agent Model (`models/agent.py`)

Represents agent state and configuration.

```python
class Agent(BaseModel):
    id: str
    name: str
    type: AgentType  # document-processor, email-handler, etc.
    status: AgentStatus  # active, idle, paused, error, disabled
    thinkingMode: ThinkingMode  # idle, exploring, structuring, validating, summarizing
    currentTaskId: Optional[str]
    constraints: List[AgentConstraint]
    permissions: AgentPermissions
    stats: AgentStats
```

**Constraint Types:**
- `ACTION_FORBIDDEN`: Disallowed operations
- `APPROVAL_REQUIRED`: Operations needing approval
- `NOTIFY_REQUIRED`: Operations requiring notification
- `LIMIT_SCOPE`: Restricted access boundaries
- `TIME_RESTRICTION`: Time-based limitations

#### 4.2.2 Task Model (`models/task.py`)

Represents work units entering the system.

```python
class Task(BaseModel):
    id: str
    title: str
    description: str
    status: TaskStatus  # pending, in_progress, completed, cancelled
    priority: TaskPriority  # low, medium, high, urgent
    source: TaskSource  # manual, slack, confluence, email
    sourceReference: Optional[str]  # Original message/document ID
    assignedAgentId: Optional[str]
    autoAssign: Optional[bool]  # Task-specific auto-assignment override
    dueDate: Optional[datetime]
    tags: List[str]
```

**Status Lifecycle:**
- `pending` → Task created, awaiting assignment
- `in_progress` → Assigned to agent, being worked on
- `completed` → Task finished successfully
- `cancelled` → Task aborted

#### 4.2.3 Approval Model (`models/approval.py`)

Manages approval requests and responses.

```python
class ApprovalRequest(BaseModel):
    id: str
    ticketId: str
    agentId: str
    type: ApprovalRequestType  # proceed, select_option, provide_input, etc.
    message: str
    context: Optional[str]
    options: Optional[List[TicketOption]]
    requiredInputs: Optional[List[RequiredInput]]
    status: ApprovalStatus  # pending, approved, rejected, expired
    response: Optional[ApprovalResponse]
    expiresAt: Optional[datetime]
    priority: int
```

#### 4.2.4 Ontology Model (`models/ontology.py`)

User-defined rules and preferences.

```python
class UserOntology(BaseModel):
    preferences: List[ThinkingPreference]  # Decision style, communication, priorities
    taboos: List[Taboo]  # Forbidden actions, timing, targets
    failurePatterns: List[FailurePattern]  # Known failure modes to avoid
    approvalRules: List[ApprovalRule]  # When to require approval
    taskTemplates: List[TaskTemplate]  # Common task patterns
    globalConstraints: List[GlobalConstraint]  # System-wide rules
```

**Taboo Severity Levels:**
- `WARNING`: Agent should reconsider
- `BLOCK`: Action prevented, requires override
- `CRITICAL`: Hard block, cannot proceed

### 4.3 Agent System

#### 4.3.1 BaseAgent (`agents/base_agent.py`)

Abstract base class for all agents following the 4-phase pipeline.

**Processing Pipeline:**

1. **Explore Phase**: Analyze input, gather relevant information
   - Decision: Should proceed? → Yes/No
   - Output: Exploration data

2. **Structure Phase**: Break down work into actionable tickets
   - Input: Exploration data
   - Output: Structured ticket proposals

3. **Validate Phase**: Check against ontology and constraints
   - Input: Structured tickets
   - Output: Validation result (valid/invalid)

4. **Summarize Phase**: Create final output with approval requests
   - Input: Validated tickets
   - Output: `AgentOutput` (tickets, approval requests, logs)

**Lifecycle Methods:**
```python
async def initialize(context: AgentExecutionContext) -> None
async def start() -> None
async def pause() -> None
async def resume() -> None
async def stop() -> None
async def process(input: AgentInput) -> AgentOutput
```

**Event Emission:**
- `state_changed`: Agent status or thinking mode updated
- `ticket_created`: New ticket generated
- `approval_requested`: Operation needs user approval
- `log`: Diagnostic information

#### 4.3.2 ThinkingModeStateMachine (`agents/thinking_mode_state_machine.py`)

Manages agent reasoning state transitions.

**State Diagram:**

```
    ┌──────┐
    │ IDLE │◄──────────────────────┐
    └──┬───┘                       │
       │ START_TASK                │
       ▼                           │
┌─────────────┐                    │
│  EXPLORING  │                    │
└──────┬──────┘                    │
       │ INFO_COLLECTED            │
       ▼                           │
┌──────────────┐                   │
│ STRUCTURING  │                   │
└──────┬───────┘                   │
       │ STRUCTURE_COMPLETE        │
       ▼                           │
┌─────────────┐                    │
│ VALIDATING  │──NO_ACTION_NEEDED──┤
└──────┬──────┘   VALIDATION_FAILED│
       │ VALIDATION_PASSED         │
       ▼                           │
┌──────────────┐                   │
│ SUMMARIZING  │                   │
└──────┬───────┘                   │
       │ TASK_COMPLETE             │
       └───────────────────────────┘
```

**Transition Events:**
- `START_TASK`: Begin processing
- `INFO_COLLECTED`: Exploration complete
- `STRUCTURE_COMPLETE`: Structuring done
- `VALIDATION_PASSED`: Validation succeeded
- `VALIDATION_FAILED`: Validation failed, return to idle
- `NO_ACTION_NEEDED`: Early exit from exploration
- `TASK_COMPLETE`: All phases done

#### 4.3.3 AgentRegistry (`agents/agent_registry.py`)

Singleton registry managing all agent instances.

**Core Functions:**
```python
def register_factory(type: str, factory: IAgentFactory) -> None
def create_agent(config: AgentConfig) -> IAgent
def register_agent(agent: IAgent) -> None
async def unregister_agent(agent_id: str) -> None
def get_agent(agent_id: str) -> Optional[IAgent]
def get_all_agents() -> List[IAgent]
def get_active_agents() -> List[IAgent]
def on_global_event(handler: AgentEventHandler) -> None
```

**Global Event Broadcasting:**
All agents are automatically subscribed to global handlers for centralized monitoring and logging.

### 4.4 MCP Services

#### 4.4.1 BaseMCPService (`mcp/base_mcp_service.py`)

Abstract base for external service integrations.

**Approval Policy:**

| Operation Type | Approval Required? | Reason |
|----------------|-------------------|---------|
| READ, SEARCH, LIST | No | Read-only, safe operations |
| CREATE, UPDATE | Optional | Service-specific policy |
| SEND, PUBLISH, SHARE | Yes | External communication |
| DELETE | Yes | Destructive operation |

**Core Methods:**
```python
async def connect() -> None
async def disconnect() -> None
async def execute(request: MCPOperationRequest) -> MCPOperationResult
async def validate(request: MCPOperationRequest) -> MCPValidationResult
async def rollback(operation_id: str) -> bool
```

**Validation Workflow:**
1. Check target validity
2. Determine if approval needed
3. Perform service-specific validation
4. Return validation result with errors/warnings

#### 4.4.2 Service Implementations

**NotionService** (`mcp/services/notion_service.py`)
- Create/read/update pages
- Search databases
- All write operations require approval

**GmailService** (`mcp/services/gmail_service.py`)
- Read emails and threads
- Create drafts (no approval)
- Send emails (requires approval)

**SlackService** (`mcp/services/slack_service.py`)
- Read messages and channels
- Create message drafts
- Send messages (requires approval)

**ConfluenceService** (`mcp/services/confluence_service.py`)
- Read pages and spaces
- Create/update pages
- Publish pages (requires approval)

#### 4.4.3 MCPServiceRegistry (`mcp/mcp_service_registry.py`)

Manages MCP service lifecycle and operation execution.

```python
def register(service: IMCPService, config: MCPServiceConfig) -> None
async def connect(service_type: str) -> None
async def disconnect(service_type: str) -> None
async def disconnect_all() -> None
def get_service(service_type: str) -> Optional[IMCPService]
async def execute_operation(request: MCPOperationRequest) -> MCPOperationResult
async def validate_operation(request: MCPOperationRequest) -> MCPValidationResult
```

### 4.5 WebSocket Server

#### 4.5.1 AgentMonitorWebSocketServer (`websocket/websocket_server.py`)

Real-time bidirectional communication with frontend.

**Connection Management:**
- Client registration with unique IDs
- Heartbeat monitoring (30-second interval)
- Automatic disconnection cleanup
- Connection count tracking

**Server-to-Client Messages:**
```python
def broadcast_agent_update(agent: Agent)
def broadcast_ticket_created(ticket: Ticket)
def broadcast_ticket_updated(ticket: Ticket)
def broadcast_approval_request(request: ApprovalRequest)
def broadcast_approval_resolved(request: ApprovalRequest)
def broadcast_notification(message: str, level: str)
def broadcast_task_created(task: Task)
```

**Client-to-Server Messages:**
- `approve_request`: User approves operation
- `reject_request`: User rejects operation
- `select_option`: User selects from options
- `provide_input`: User provides required input
- `pause_agent`: Pause agent execution
- `resume_agent`: Resume paused agent
- `cancel_ticket`: Cancel pending ticket

### 4.6 Slack Integration

#### 4.6.1 SlackWebhookService (`services/slack_webhook.py`)

Processes incoming Slack events and converts to tasks.

**Supported Events:**
- `app_mention`: Bot mentioned in channel
- `message` (channel_type: im): Direct message to bot

**Task Creation Logic:**
```python
def _handle_mention(event) -> Task:
    # Remove mentions from text
    # Create task with priority=MEDIUM, source=SLACK
    # Set autoAssign=True (Slack tasks auto-assign by default)

def _handle_dm(event) -> Task:
    # Extract DM text
    # Create task with priority=MEDIUM, source=SLACK
    # Set autoAssign=True
```

**Security:**
- Signature verification using `SLACK_SIGNING_SECRET`
- Timestamp validation (5-minute window)
- HMAC-SHA256 signature comparison

#### 4.6.2 Slack Webhook API (`api/slack_webhook.py`)

FastAPI endpoint receiving Slack events.

```python
@router.post("/api/slack/webhook")
async def slack_webhook(request: Request):
    # 1. Verify Slack signature
    # 2. Handle URL verification challenge
    # 3. Process event_callback
    # 4. Convert to Task
    # 5. Broadcast via WebSocket
```

---

## 5. Data Flow

### 5.1 Task Creation Flow

#### From Slack

```
Slack User mentions bot
         │
         ▼
Slack sends webhook POST to /api/slack/webhook
         │
         ▼
SlackWebhookService.process_event()
         │
         ▼
Create Task (source=SLACK, autoAssign=true)
         │
         ▼
Call task_created handlers
         │
         ▼
WebSocketServer.broadcast_task_created()
         │
         ▼
Frontend receives task_created message
         │
         ▼
App.tsx updates tasks state
         │
         ▼
OrchestrationService.selectAgentForTask()
         │
         ▼
LLM analyzes task and agents
         │
         ▼
Task assigned to selected agent
         │
         ▼
Agent processes task (4-phase pipeline)
```

#### Manual Creation

```
User fills CreateTaskModal form
         │
         ▼
handleCreateTask(input: CreateTaskInput)
         │
         ▼
Create Task locally
         │
         ▼
Add to tasks state
         │
         ▼
Check autoAssign conditions
         │
         ▼
If eligible: OrchestrationService.selectAgentForTask()
         │
         ▼
Assign to agent
```

### 5.2 Agent Processing Flow

```
Task created (Slack/Manual)
         │
         ▼
Auto-assignment check (autoAssign mode)
         │
         ├─ Auto-assign eligible?
         │  ├─ Yes → OrchestrationService.selectAgentForTask()
         │  │         │
         │  │         ▼
         │  │  Agent selected
         │  │         │
         │  │         ▼
         │  │  Task status updated (in_progress)
         │  │         │
         │  │         ▼
         │  └─ Frontend sends assign_task WebSocket message
         │
         └─ No → Wait for manual assignment
                │
                ▼
         User manually assigns Task
                │
                ▼
         Frontend sends assign_task WebSocket message
         │
         ▼
Backend receives assign_task
         │
         ▼
Backend finds or creates Agent
         │
         ▼
Agent 초기화 및 시작 (initialize, start)
         │
         ▼
process_agent_task() 호출
         │
         ▼
Agent 상태 업데이트 (currentTaskId 설정)
         │
         ▼
agent.process(input: AgentInput)
         │
         ▼
┌──────────────────┐
│  EXPLORE PHASE   │
│ - Analyze input  │
│ - Gather info    │
│ - Decide proceed │
└────────┬─────────┘
         │ should_proceed=true
         ▼
┌──────────────────┐
│ STRUCTURE PHASE  │
│ - Break down     │
│ - Create tickets │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ VALIDATE PHASE   │
│ - Check ontology │
│ - Verify rules   │
└────────┬─────────┘
         │ is_valid=true
         ▼
┌──────────────────┐
│ SUMMARIZE PHASE  │
│ - Generate output│
│ - Create approvals│
└────────┬─────────┘
         │
         ▼
Return AgentOutput (tickets, approvals, logs)
         │
         ▼
process_agent_task()에서 결과 처리
         │
         ├─ Tickets 추출 → broadcast_ticket_created()
         ├─ Approvals 추출 → broadcast_approval_request()
         └─ Agent 상태 업데이트 (currentTaskId 제거)
         │
         ▼
WebSocket broadcasts to frontend
         │
         ▼
Tickets and Approvals appear in UI
```

### 5.3 Approval Flow

```
Agent creates Ticket requiring approval
         │
         ▼
Emit approval_requested event
         │
         ▼
WebSocket broadcasts ApprovalRequest
         │
         ▼
Frontend adds to approvalQueue
         │
         ▼
User sees ApprovalQueue component
         │
         ▼
User responds (approve/reject/select/input)
         │
         ▼
handleApprovalRespond(requestId, response)
         │
         ▼
Update ticket status
         │
         ▼
WebSocket sends approval response to backend
         │
         ▼
Agent.on_approval_received(approval)
         │
         ├── If approved: agent.on_approved()
         │   └── Execute operation via MCP service
         │
         └── If rejected: agent.on_rejected()
             └── Log rejection, cleanup
```

### 5.4 MCP Operation Flow

```
Agent needs to perform operation (e.g., send email)
         │
         ▼
Create MCPOperationRequest
         │
         ▼
mcp_registry.validate_operation(request)
         │
         ▼
Check if approval required
         │
         ├── If no: Execute immediately
         │
         └── If yes: Create ApprovalRequest
                     │
                     ▼
            Wait for user approval
                     │
                     ▼
            User approves
                     │
                     ▼
            mcp_registry.execute_operation(request)
                     │
                     ▼
            service._do_execute(request)
                     │
                     ▼
            Call external API
                     │
                     ▼
            Return MCPOperationResult
                     │
                     ▼
            Broadcast result to frontend
```

### 5.5 Real-time State Synchronization

```
Backend State Change (agent status, ticket created, etc.)
         │
         ▼
Agent/Service emits event
         │
         ▼
Event handler in main.py receives event
         │
         ▼
WebSocketServer.broadcast_*() called
         │
         ▼
Message serialized to JSON
         │
         ▼
Send to all connected WebSocket clients
         │
         ▼
Frontend useWebSocket hook receives message
         │
         ▼
handleMessage(message: WebSocketMessage)
         │
         ├── agent_update → Update agents state
         ├── ticket_created → Add to tickets state
         ├── ticket_updated → Update tickets state
         ├── approval_request → Add to approvalQueue
         ├── task_created → Add to tasks state
         └── system_notification → Show notification
         │
         ▼
React re-renders affected components
```

---

## 6. Key Features

### 6.1 Agent Lifecycle Management

**Creation:**
```typescript
// Frontend - CreateAgentModal
const config: CustomAgentConfig = {
  name: "Email Handler",
  type: "email-handler",
  description: "Handles customer support emails",
  constraints: ["Cannot send emails without approval"],
  permissions: {
    canAccessMcp: ["gmail"],
  },
};
handleCreateAgent(config);
```

```python
# Backend - Agent creation
from agents import agent_registry, AgentConfig

config = AgentConfig(
    name="Email Handler",
    type="email-handler",
    description="Handles customer support emails",
    constraints=[
        {"type": "approval_required", "description": "All email sends"}
    ],
    permissions={
        "canAccessMcp": ["gmail"]
    }
)
agent = agent_registry.create_agent(config)
await agent.initialize(context)
await agent.start()
```

**State Transitions:**
- `idle` → `active`: agent.start()
- `active` → `paused`: agent.pause()
- `paused` → `active`: agent.resume()
- `active` → `idle`: agent.stop()
- Any → `error`: Exception during processing

**Monitoring:**
- Real-time status updates via WebSocket
- Thinking mode visibility (explore, structure, validate, summarize)
- Current task description
- Statistics (tickets created/completed/rejected)

### 6.2 Task Assignment and Orchestration

#### Orchestration Service

Uses LLM to analyze tasks and select optimal agents.

```typescript
async selectAgentForTask(task: Task, agents: Agent[]): Promise<string | null> {
  // 1. Create agent summary (id, name, type, isActive, currentTask)
  // 2. Build LLM prompt with task details and agent options
  // 3. Call LLM with structured output request
  // 4. Parse JSON response
  // 5. Validate selected agent exists and is available
  // 6. Return agent ID or null
}
```

**Selection Criteria:**
- Agent type relevance to task content
- Agent availability (not currently working)
- Task priority alignment
- Agent specialization (tags, MCP access)

#### Auto-Assignment Modes

**Global Mode** (`autoAssignMode: 'global'`):
- All new tasks automatically assigned unless `autoAssign: false`
- Suitable for fully automated workflows
- User can opt-out per task

**Manual Mode** (`autoAssignMode: 'manual'`):
- Only tasks with `autoAssign: true` assigned automatically
- Default rules still apply (high priority, Slack-sourced)
- Suitable for human-in-loop workflows

**Default Auto-Assignment Rules:**
```typescript
shouldAutoAssign(task: Task): boolean {
  if (task.priority === 'urgent' || task.priority === 'high') {
    return true;
  }
  if (task.source === 'slack') {
    return true;
  }
  return false;
}
```

### 6.3 Approval Workflow

#### Approval Types

**1. Proceed Approval**
Simple binary decision.
```python
ApprovalRequest(
    type=ApprovalRequestType.PROCEED,
    message="Send email to customer@example.com?",
    context="Subject: Re: Support Request #1234"
)
```

**2. Select Option**
Choose from alternatives.
```python
ApprovalRequest(
    type=ApprovalRequestType.SELECT_OPTION,
    message="Multiple matching contacts found. Which one?",
    options=[
        TicketOption(id="1", label="John Doe (john@company.com)"),
        TicketOption(id="2", label="Jane Doe (jane@company.com)"),
    ]
)
```

**3. Provide Input**
Fill required fields.
```python
ApprovalRequest(
    type=ApprovalRequestType.PROVIDE_INPUT,
    message="Please provide meeting details",
    requiredInputs=[
        RequiredInput(key="date", label="Meeting Date", type=InputType.DATE),
        RequiredInput(key="attendees", label="Attendees", type=InputType.TEXT),
    ]
)
```

**4. Confirm Action**
Verify before destructive operation.
```python
ApprovalRequest(
    type=ApprovalRequestType.CONFIRM_ACTION,
    message="Delete 50 emails from inbox?",
    context="This action cannot be undone"
)
```

**5. Review Result**
Validate agent output.
```python
ApprovalRequest(
    type=ApprovalRequestType.REVIEW_RESULT,
    message="Review generated report",
    context="<report content>"
)
```

#### Approval Response Handling

```python
async def on_approval_received(self, approval: ApprovalRequest):
    if approval.status == ApprovalStatus.APPROVED:
        # Execute approved operation
        await self.on_approved(approval)

        # Update stats
        self._state.stats.ticketsCompleted += 1

    elif approval.status == ApprovalStatus.REJECTED:
        # Handle rejection
        await self.on_rejected(approval)

        # Update stats
        self._state.stats.ticketsRejected += 1

    self._emit_state_change()
```

### 6.4 WebSocket Real-time Communication

#### Connection Lifecycle

```typescript
const ws = new WebSocket('ws://localhost:8080');

ws.onopen = () => {
  console.log('Connected');
  setIsConnected(true);
};

ws.onmessage = (event) => {
  const message: WebSocketMessage = JSON.parse(event.data);
  handleMessage(message);
};

ws.onclose = () => {
  console.log('Disconnected');
  setIsConnected(false);
  scheduleReconnect(); // Automatic reconnection
};
```

#### Message Types

**Server → Client:**
- `agent_update`: Agent state changed
- `ticket_created`: New ticket generated
- `ticket_updated`: Ticket status changed
- `approval_request`: Approval needed
- `approval_resolved`: Approval processed
- `task_created`: New task added
- `system_notification`: System message

**Client → Server:**
- `approve_request`: Approve operation
- `reject_request`: Reject operation
- `select_option`: Choose option
- `provide_input`: Submit input
- `pause_agent`: Pause agent
- `resume_agent`: Resume agent
- `cancel_ticket`: Cancel ticket

#### Heartbeat Mechanism

**Backend:**
```python
async def _heartbeat_loop(self):
    while True:
        await asyncio.sleep(30)
        for client in self.clients.values():
            if not client.is_alive:
                await client.websocket.close()
            else:
                client.is_alive = False
                await client.websocket.ping()
```

**Frontend:**
Auto-reconnection on disconnect with exponential backoff (max 5 attempts).

### 6.5 Slack Integration

#### Setup Requirements

1. Create Slack App at https://api.slack.com/apps
2. Enable Event Subscriptions
3. Set Request URL: `https://<your-domain>/api/slack/webhook`
4. Subscribe to bot events:
   - `app_mention`
   - `message.im`
   - `message.channels` (optional)
5. Install app to workspace
6. Copy Bot Token and Signing Secret to `.env`

#### Event Processing

**URL Verification:**
```python
if event_type == "url_verification":
    challenge = event_data.get("challenge")
    return {"challenge": challenge}
```

**Event Callback:**
```python
if event_type == "event_callback":
    event = event_data.get("event")

    if event["type"] == "app_mention":
        task = _handle_mention(event)
    elif event["type"] == "message" and event["channel_type"] == "im":
        task = _handle_dm(event)

    broadcast_task_created(task)
```

#### Task Creation from Slack

```python
def _handle_mention(event):
    text = event["text"]
    cleaned_text = remove_mentions(text)

    return Task(
        title=f"Slack mention: {cleaned_text[:50]}",
        description=f"Channel: {event['channel']}\nMessage: {cleaned_text}",
        priority=TaskPriority.MEDIUM,
        source=TaskSource.SLACK,
        sourceReference=f"{event['channel']}:{event['ts']}",
        tags=["slack", "mention"],
        autoAssign=True  # Slack tasks auto-assign by default
    )
```

### 6.6 Task Detail View and Progress Tracking

#### Task Detail Modal

Each task has a detailed view accessible via the "View Detail" button, showing:

**Features:**
- **Overview Tab**: Complete task information, metadata, and current status
- **Tickets Tab**: All tickets created by the agent for this task
- **Approvals Tab**: All approval requests related to the task
- **Agent Progress**: Real-time agent thinking mode and current activity

**Usage:**
```typescript
// TaskCard component now has a detail view button
<TaskCard
  task={task}
  agents={agents}
  onViewDetail={(taskId) => {
    // Opens TaskDetailModal with full tracking information
  }}
  // ... other props
/>
```

**Detail View Contents:**

1. **Task Overview**
   - Title, description, status, priority
   - Source (Slack, Manual, etc.)
   - Tags and metadata
   - Creation, update, completion timestamps
   - Due date (if set)

2. **Agent Progress Tracking**
   - Current thinking mode (idle, exploring, structuring, validating, summarizing)
   - Current task description
   - Agent name and type

3. **Related Tickets**
   - All tickets created by the assigned agent
   - Ticket status (pending_approval, approved, in_progress, completed, rejected)
   - Execution plans and decision requirements

4. **Approval Requests**
   - All approval requests for the task
   - Request type (proceed, select_option, prioritize)
   - Available options with recommendations
   - Approval status

**Benefits:**
- **Transparency**: Full visibility into agent progress
- **Debugging**: Easy identification of bottlenecks
- **Auditing**: Complete history of task execution
- **Context**: Understanding why approvals were requested

### 6.7 Data Persistence with localStorage

#### Automatic State Persistence

The application automatically saves and restores state across browser sessions using localStorage.

**Persisted Data:**
- **Settings**: MCP services, LLM configuration, API keys
- **Auto-assign Mode**: Global or manual task assignment preference
- **Custom Agents**: User-created agent configurations
- **Personalization Items**: Saved insights and preferences

**Implementation:**

```typescript
// src/utils/localStorage.ts
import { saveToLocalStorage, loadFromLocalStorage } from './utils/localStorage';

// Automatic save on state change
useEffect(() => {
  saveToLocalStorage('SETTINGS', settings);
}, [settings]);

// Load on component mount
const [settings, setSettings] = useState<AppSettings>(() => {
  const saved = loadFromLocalStorage<AppSettings>('SETTINGS');
  return saved || initialSettings;
});
```

**Storage Keys:**
```typescript
const STORAGE_KEYS = {
  SETTINGS: 'agent-monitor-settings',
  TASKS: 'agent-monitor-tasks',
  AGENTS: 'agent-monitor-agents',
  TICKETS: 'agent-monitor-tickets',
  APPROVALS: 'agent-monitor-approvals',
  AUTO_ASSIGN_MODE: 'agent-monitor-auto-assign-mode',
  CUSTOM_AGENTS: 'agent-monitor-custom-agents',
  PERSONALIZATION: 'agent-monitor-personalization',
};
```

**Benefits:**
- **Session Continuity**: Work resumes after page refresh
- **Configuration Persistence**: No need to reconfigure on restart
- **Offline Capability**: Settings available without server
- **User Preferences**: Personalization survives browser restarts

**API:**

```typescript
// Save data
saveToLocalStorage('SETTINGS', settingsObject);

// Load data
const settings = loadFromLocalStorage<AppSettings>('SETTINGS');

// Remove data
removeFromLocalStorage('SETTINGS');

// Clear all
clearAllStorage();
```

**Error Handling:**
- Graceful fallback to defaults if localStorage unavailable
- Console logging for debugging
- Automatic JSON serialization/deserialization

### 6.8 MCP Service Integration

#### Service Registration

```python
# main.py
notion_service = NotionService(MCPServiceConfig(
    type="notion",
    name="Notion Workspace",
    enabled=True,
    credentials={"apiKey": os.getenv("NOTION_API_KEY")}
))

mcp_registry.register(notion_service, config)
await mcp_registry.connect("notion")
```

#### Operation Execution

```python
# Agent code
request = MCPOperationRequest(
    id=str(uuid4()),
    operation=MCPOperationType.CREATE,
    target=MCPOperationTarget(type="page", id=None),
    payload={
        "title": "Meeting Notes",
        "content": "...",
    },
    requiresApproval=True,
    status=ApprovalStatus.PENDING
)

# Validate first
validation = await mcp_registry.validate_operation(request)
if not validation.isValid:
    raise ValueError(validation.errors)

# If approval required, create approval request
if validation.requiresApproval:
    approval = ApprovalRequest(
        ticketId=ticket_id,
        agentId=self.id,
        type=ApprovalRequestType.PROCEED,
        message=validation.approvalReason,
        context=json.dumps(request.payload)
    )
    # Emit approval request event
    # Wait for user approval...

# Execute after approval
request.status = ApprovalStatus.APPROVED
result = await mcp_registry.execute_operation(request)
```

#### Service-Specific Policies

**Notion:**
- All CREATE/UPDATE operations require approval
- READ operations freely allowed

**Gmail:**
- CREATE (drafts) allowed without approval
- SEND requires approval
- DELETE requires approval

**Slack:**
- CREATE (draft message) requires approval
- SEND requires approval
- READ operations allowed

**Confluence:**
- CREATE/UPDATE drafts allowed
- PUBLISH requires approval
- DELETE requires approval

---

## 7. Setup and Configuration

### 7.1 Prerequisites

- **Node.js**: 18.x or higher
- **Python**: 3.9 or higher
- **npm**: 8.x or higher
- **pip**: 21.x or higher

### 7.2 Installation Steps

#### Frontend Setup

```bash
# Navigate to project root
cd agent-monitor_v2

# Install dependencies
npm install

# Start development server
npm run dev
```

Development server runs at `http://localhost:5173`

#### Backend Setup

```bash
# Navigate to backend directory
cd server_python

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env  # If exists, otherwise create manually

# Start backend server
python main.py
```

Backend servers:
- WebSocket: `ws://localhost:8080`
- HTTP API: `http://localhost:8000`

### 7.3 Environment Variables

Create `server_python/.env` file:

```bash
# Server Ports
WS_PORT=8080          # WebSocket server port
HTTP_PORT=8000        # HTTP API server port

# Notion Integration
NOTION_API_KEY=your_notion_key_here

# Slack Integration
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_SIGNING_SECRET=your_signing_secret_here
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Gmail Integration (OAuth2)
GMAIL_CLIENT_ID=your_client_id
GMAIL_CLIENT_SECRET=your_client_secret

# Confluence Integration
CONFLUENCE_URL=https://your-domain.atlassian.net
CONFLUENCE_USERNAME=your_email@example.com
CONFLUENCE_API_TOKEN=your_api_token

# LLM Configuration (for orchestration)
ANTHROPIC_API_KEY=your_anthropic_key  # Optional, for LLM features
OPENAI_API_KEY=your_openai_key        # Optional, alternative LLM
```

### 7.4 Configuration Files

#### Frontend Configuration

**vite.config.ts:**
```typescript
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Proxy WebSocket connections
      '/ws': {
        target: 'ws://localhost:8080',
        ws: true,
      },
    },
  },
});
```

**tailwind.config.js:**
```javascript
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};
```

#### Backend Configuration

**main.py startup:**
```python
# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production: specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket server
ws_server = AgentMonitorWebSocketServer(port=8080)

# HTTP server for Slack webhooks
uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 7.5 Local Development with ngrok (for Slack)

Slack webhooks require publicly accessible HTTPS URLs.

```bash
# Install ngrok
brew install ngrok  # macOS
# or download from https://ngrok.com/download

# Start ngrok tunnel
ngrok http 8000

# Output shows forwarding URL:
# Forwarding: https://abc123.ngrok.io -> http://localhost:8000

# Use this URL in Slack Event Subscriptions:
# https://abc123.ngrok.io/api/slack/webhook
```

**Important:** ngrok URLs change on restart. Update Slack settings after each restart.

### 7.6 Production Deployment

#### Frontend Build

```bash
npm run build
```

Output in `dist/` directory. Serve with nginx, Apache, or CDN.

#### Backend Deployment

**Using Uvicorn:**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Using Gunicorn:**
```bash
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

**Using Docker:**
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000 8080

CMD ["python", "main.py"]
```

#### Reverse Proxy (nginx)

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    # Frontend
    location / {
        root /var/www/agent-monitor/dist;
        try_files $uri /index.html;
    }

    # Backend HTTP
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket
    location /ws {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## 8. API Documentation

### 8.1 WebSocket Events

#### Connection

**Endpoint:** `ws://localhost:8080`

**Connection Message (Server → Client):**
```json
{
  "type": "system_notification",
  "payload": {
    "message": "Connected to Agent Monitor"
  },
  "timestamp": "2025-01-15T10:30:00.000Z"
}
```

#### Server → Client Events

**agent_update:**
```json
{
  "type": "agent_update",
  "payload": {
    "id": "agent-123",
    "name": "Email Handler",
    "type": "email-handler",
    "status": "active",
    "thinkingMode": "exploring",
    "currentTaskId": "task-456",
    "currentTaskDescription": "Process customer email",
    "constraints": [...],
    "permissions": {...},
    "stats": {...},
    "lastActivity": "2025-01-15T10:30:00.000Z",
    "createdAt": "2025-01-15T09:00:00.000Z",
    "updatedAt": "2025-01-15T10:30:00.000Z"
  },
  "timestamp": "2025-01-15T10:30:00.000Z"
}
```

**ticket_created:**
```json
{
  "type": "ticket_created",
  "payload": {
    "id": "ticket-789",
    "agentId": "agent-123",
    "type": "action",
    "title": "Send email to customer",
    "description": "Reply to support request #1234",
    "priority": "high",
    "status": "pending_approval",
    "requiresApproval": true,
    "estimatedDuration": 300000,
    "createdAt": "2025-01-15T10:30:00.000Z"
  },
  "timestamp": "2025-01-15T10:30:00.000Z"
}
```

**approval_request:**
```json
{
  "type": "approval_request",
  "payload": {
    "id": "approval-101",
    "ticketId": "ticket-789",
    "agentId": "agent-123",
    "type": "proceed",
    "message": "Send email to customer@example.com?",
    "context": "Subject: Re: Support Request #1234",
    "status": "pending",
    "priority": 1,
    "createdAt": "2025-01-15T10:30:00.000Z"
  },
  "timestamp": "2025-01-15T10:30:00.000Z"
}
```

**task_created:**
```json
{
  "type": "task_created",
  "payload": {
    "id": "task-456",
    "title": "Slack mention: Help needed",
    "description": "Channel: #support\nMessage: Help needed with login issue",
    "status": "pending",
    "priority": "medium",
    "source": "slack",
    "sourceReference": "C12345:1234567890.123456",
    "assignedAgentId": null,
    "autoAssign": true,
    "tags": ["slack", "mention"],
    "createdAt": "2025-01-15T10:30:00.000Z",
    "updatedAt": "2025-01-15T10:30:00.000Z"
  },
  "timestamp": "2025-01-15T10:30:00.000Z"
}
```

#### Client → Server Events

**approve_request:**
```json
{
  "type": "approve_request",
  "payload": {
    "requestId": "approval-101",
    "comment": "Looks good"
  },
  "timestamp": "2025-01-15T10:31:00.000Z"
}
```

**reject_request:**
```json
{
  "type": "reject_request",
  "payload": {
    "requestId": "approval-101",
    "reason": "Wrong recipient"
  },
  "timestamp": "2025-01-15T10:31:00.000Z"
}
```

**select_option:**
```json
{
  "type": "select_option",
  "payload": {
    "requestId": "approval-102",
    "optionId": "option-1"
  },
  "timestamp": "2025-01-15T10:31:00.000Z"
}
```

**provide_input:**
```json
{
  "type": "provide_input",
  "payload": {
    "requestId": "approval-103",
    "inputValues": {
      "date": "2025-01-20",
      "attendees": "john@example.com, jane@example.com"
    }
  },
  "timestamp": "2025-01-15T10:31:00.000Z"
}
```

### 8.2 HTTP Endpoints

#### Slack Webhook

**POST /api/slack/webhook**

Receives Slack events.

**Headers:**
```
Content-Type: application/json
X-Slack-Request-Timestamp: 1234567890
X-Slack-Signature: v0=abc123...
```

**Request Body (URL Verification):**
```json
{
  "type": "url_verification",
  "challenge": "3eZbrw1aBm2rZgRNFdxV2595E9CY3gmdALWMmHkvFXO7tYXAYM8P",
  "token": "Jhj5dZrVaK7ZwHHjRyZWjbDl"
}
```

**Response:**
```json
{
  "challenge": "3eZbrw1aBm2rZgRNFdxV2595E9CY3gmdALWMmHkvFXO7tYXAYM8P"
}
```

**Request Body (Event Callback):**
```json
{
  "type": "event_callback",
  "event": {
    "type": "app_mention",
    "user": "U12345",
    "text": "<@U_BOT> Help needed with login issue",
    "ts": "1234567890.123456",
    "channel": "C12345",
    "event_ts": "1234567890.123456"
  },
  "event_time": 1234567890
}
```

**Response:**
```json
{
  "status": "ok"
}
```

### 8.3 MCP Operations

#### Operation Request Structure

```python
MCPOperationRequest(
    id="op-123",
    operation=MCPOperationType.CREATE,  # READ, CREATE, UPDATE, DELETE, SEND, etc.
    target=MCPOperationTarget(
        type="email",  # page, message, document, etc.
        id="optional-target-id"
    ),
    payload={
        # Operation-specific data
    },
    requiresApproval=True,
    status=ApprovalStatus.PENDING
)
```

#### Validation Response

```python
MCPValidationResult(
    isValid=True,
    errors=[],
    warnings=["Message will be sent to external recipient"],
    requiresApproval=True,
    approvalReason="External communication requires approval"
)
```

#### Operation Result

```python
MCPOperationResult(
    success=True,
    data={
        "id": "email-123",
        "status": "sent",
        "timestamp": "2025-01-15T10:30:00Z"
    },
    metadata={
        "message": "Email sent successfully"
    }
)
```

#### Example: Send Email via Gmail

```python
# 1. Create operation request
request = MCPOperationRequest(
    id=str(uuid4()),
    operation=MCPOperationType.SEND,
    target=MCPOperationTarget(type="email"),
    payload={
        "to": "customer@example.com",
        "subject": "Re: Support Request #1234",
        "body": "Hello,\n\nThank you for contacting us..."
    },
    requiresApproval=True,
    status=ApprovalStatus.PENDING
)

# 2. Validate operation
validation = await mcp_registry.validate_operation(request)
if not validation.isValid:
    raise ValueError(validation.errors)

# 3. Request approval (if needed)
if validation.requiresApproval:
    approval = await request_user_approval(
        message=validation.approvalReason,
        context=json.dumps(request.payload)
    )
    if approval.status != ApprovalStatus.APPROVED:
        return
    request.status = ApprovalStatus.APPROVED

# 4. Execute operation
result = await mcp_registry.execute_operation(request)
if result.success:
    print(f"Email sent: {result.data['id']}")
else:
    print(f"Failed: {result.error}")
```

---

## 9. Extending the System

### 9.1 Creating Custom Agents

#### Step 1: Define Agent Class

Create `server_python/agents/custom_agent.py`:

```python
from agents.base_agent import BaseAgent
from agents.types import AgentConfig, AgentInput, AgentOutput
from models.ticket import Ticket, TicketType
from typing import Dict, Any

class CustomAgent(BaseAgent):
    """
    Custom agent for specific domain logic.
    Implements the 4-phase pipeline: explore → structure → validate → summarize
    """

    async def explore(self, input: AgentInput) -> Dict[str, Any]:
        """
        Phase 1: Analyze input and gather relevant information.

        Returns:
            {
                "should_proceed": bool,
                "data": Any  # Data for next phase
            }
        """
        self.log("info", f"Exploring input: {input.content}")

        # Analyze input
        # Gather necessary information
        # Decide if processing should continue

        return {
            "should_proceed": True,
            "data": {
                # Collected information
            }
        }

    async def structure(self, data: Any) -> Any:
        """
        Phase 2: Break down work into actionable tickets.

        Returns:
            Structured data representing tickets to create
        """
        self.log("info", "Structuring work into tickets")

        # Break down work
        # Identify discrete tasks
        # Create ticket proposals

        return {
            "tickets": [
                {
                    "type": TicketType.ACTION,
                    "title": "Perform specific action",
                    "description": "Detailed description",
                    "priority": "medium"
                }
            ]
        }

    async def validate(self, data: Any) -> Dict[str, Any]:
        """
        Phase 3: Validate against ontology and constraints.

        Returns:
            {
                "is_valid": bool,
                "data": Any,  # Validated data
                "errors": List[str]
            }
        """
        self.log("info", "Validating structured data")

        # Check constraints
        # Verify against ontology rules
        # Validate data integrity

        errors = []

        # Example: Check constraint
        if self._has_constraint("ACTION_FORBIDDEN", "delete_data"):
            errors.append("Delete operations are forbidden")

        return {
            "is_valid": len(errors) == 0,
            "data": data,
            "errors": errors
        }

    async def summarize(self, data: Any) -> AgentOutput:
        """
        Phase 4: Generate final output with tickets and approval requests.

        Returns:
            AgentOutput containing tickets, approvals, and logs
        """
        self.log("info", "Summarizing and creating output")

        tickets = []
        approval_requests = []

        # Create tickets from structured data
        for ticket_data in data.get("tickets", []):
            ticket = Ticket(
                agentId=self.id,
                type=ticket_data["type"],
                title=ticket_data["title"],
                description=ticket_data["description"],
                priority=ticket_data["priority"],
                requiresApproval=True  # Determine based on operation
            )
            tickets.append(ticket)

            # Create approval request if needed
            if ticket.requiresApproval:
                from models.approval import ApprovalRequest, ApprovalRequestType
                approval = ApprovalRequest(
                    ticketId=ticket.id,
                    agentId=self.id,
                    type=ApprovalRequestType.PROCEED,
                    message=f"Approve: {ticket.title}",
                    context=ticket.description
                )
                approval_requests.append(approval)

        return AgentOutput(
            tickets=tickets,
            approval_requests=approval_requests,
            logs=[f"Created {len(tickets)} tickets"]
        )

    def _has_constraint(self, constraint_type: str, condition: str) -> bool:
        """Check if agent has specific constraint."""
        for constraint in self._state.constraints:
            if constraint.type == constraint_type and constraint.condition == condition:
                return constraint.isActive
        return False
```

#### Step 2: Register Agent Factory

Create `server_python/agents/custom_agent_factory.py`:

```python
from agents.types import IAgentFactory, IAgent, AgentConfig
from agents.custom_agent import CustomAgent

class CustomAgentFactory(IAgentFactory):
    def create(self, config: AgentConfig) -> IAgent:
        return CustomAgent(config)
```

#### Step 3: Register in main.py

```python
from agents import agent_registry
from agents.custom_agent_factory import CustomAgentFactory

# Register factory
agent_registry.register_factory("custom-agent", CustomAgentFactory())

# Create agent instance
from agents.types import AgentConfig

config = AgentConfig(
    name="My Custom Agent",
    type="custom-agent",
    description="Performs custom domain logic",
    constraints=[],
    permissions={}
)

agent = agent_registry.create_agent(config)
await agent.initialize(context)
await agent.start()
```

### 9.2 Adding New MCP Services

#### Step 1: Implement Service Class

Create `server_python/mcp/services/custom_service.py`:

```python
from typing import Dict, Any
from ..base_mcp_service import BaseMCPService
from ..types import (
    MCPServiceConfig,
    MCPOperationRequest,
    MCPOperationResult,
    MCPOperationType,
)

class CustomService(BaseMCPService):
    """
    Custom MCP service integration.
    Implement connection, operations, and validation.
    """

    def __init__(self, config: MCPServiceConfig):
        super().__init__(config)
        self.api_key = config.credentials.get("apiKey") if config.credentials else None
        self.client = None  # External API client

    async def _do_connect(self) -> None:
        """Establish connection to external service."""
        if not self.api_key:
            raise ValueError("API key required")

        # Initialize API client
        # self.client = CustomAPIClient(api_key=self.api_key)

        print(f"[CustomService] Connected")

    async def _do_disconnect(self) -> None:
        """Close connection to external service."""
        # Clean up resources
        # if self.client:
        #     await self.client.close()

        print(f"[CustomService] Disconnected")

    async def _do_execute(self, request: MCPOperationRequest) -> MCPOperationResult:
        """Execute operation on external service."""
        operation = request.operation
        target = request.target
        payload = request.payload

        if operation == MCPOperationType.READ:
            return await self._read(target.id)

        elif operation == MCPOperationType.CREATE:
            return await self._create(payload)

        elif operation == MCPOperationType.UPDATE:
            return await self._update(target.id, payload)

        elif operation == MCPOperationType.DELETE:
            return await self._delete(target.id)

        else:
            return MCPOperationResult(
                success=False,
                error=f"Unsupported operation: {operation}"
            )

    async def _do_validate(self, request: MCPOperationRequest) -> Dict[str, list]:
        """Validate operation request."""
        errors = []
        warnings = []

        # Validate payload structure
        if request.operation in [MCPOperationType.CREATE, MCPOperationType.UPDATE]:
            if not request.payload.get("required_field"):
                errors.append("required_field is missing")

        # Add warnings for risky operations
        if request.operation == MCPOperationType.DELETE:
            warnings.append("This operation is irreversible")

        return {"errors": errors, "warnings": warnings}

    def _should_require_approval(self, request: MCPOperationRequest) -> bool:
        """Determine if operation requires approval."""
        # Custom approval logic
        if request.operation == MCPOperationType.CREATE:
            # Require approval for large operations
            if request.payload.get("size", 0) > 1000:
                return True

        # Default to parent class logic
        return super()._should_require_approval(request)

    # === Service-specific operations ===

    async def _read(self, resource_id: str) -> MCPOperationResult:
        """Read resource from external service."""
        print(f"[CustomService] Reading resource: {resource_id}")

        # Call external API
        # data = await self.client.get(resource_id)

        return MCPOperationResult(
            success=True,
            data={"id": resource_id, "content": "..."}
        )

    async def _create(self, data: Dict[str, Any]) -> MCPOperationResult:
        """Create resource in external service."""
        print(f"[CustomService] Creating resource")

        # Call external API
        # result = await self.client.create(data)

        return MCPOperationResult(
            success=True,
            data={"id": "new-resource-id"},
            metadata={"message": "Resource created"}
        )

    async def _update(self, resource_id: str, data: Dict[str, Any]) -> MCPOperationResult:
        """Update resource in external service."""
        print(f"[CustomService] Updating resource: {resource_id}")

        # Call external API
        # result = await self.client.update(resource_id, data)

        return MCPOperationResult(
            success=True,
            data={"id": resource_id},
            metadata={"message": "Resource updated"}
        )

    async def _delete(self, resource_id: str) -> MCPOperationResult:
        """Delete resource from external service."""
        print(f"[CustomService] Deleting resource: {resource_id}")

        # Call external API
        # await self.client.delete(resource_id)

        return MCPOperationResult(
            success=True,
            metadata={"message": "Resource deleted"}
        )
```

#### Step 2: Register Service

In `server_python/mcp/services/__init__.py`:

```python
from .custom_service import CustomService

__all__ = [
    "NotionService",
    "GmailService",
    "SlackService",
    "ConfluenceService",
    "CustomService",  # Add here
]
```

In `server_python/main.py`:

```python
from mcp import mcp_registry, CustomService
from mcp.types import MCPServiceConfig

# Create service instance
custom_service = CustomService(MCPServiceConfig(
    type="custom",
    name="Custom Integration",
    enabled=True,
    credentials={"apiKey": os.getenv("CUSTOM_API_KEY")}
))

# Register service
mcp_registry.register(custom_service, MCPServiceConfig(
    type="custom",
    name="Custom Integration",
    enabled=True
))

# Connect
await mcp_registry.connect("custom")
```

### 9.3 Custom Constraints

#### Ontology-Based Constraints

Add to user ontology:

```python
from models.ontology import (
    UserOntology,
    Taboo,
    TabooType,
    TabooSeverity,
    ApprovalRule,
    ApprovalConditionType,
    ApprovalType
)

ontology = UserOntology(
    userId="user-123",
    taboos=[
        Taboo(
            type=TabooType.ACTION,
            description="Never delete customer data",
            severity=TabooSeverity.CRITICAL,
            condition="operation == 'delete' AND target.contains('customer')"
        ),
        Taboo(
            type=TabooType.TIMING,
            description="No automated emails on weekends",
            severity=TabooSeverity.BLOCK,
            condition="day_of_week in ['Saturday', 'Sunday']"
        )
    ],
    approvalRules=[
        ApprovalRule(
            name="High-value transactions",
            description="Require approval for transactions over $1000",
            condition=ApprovalCondition(
                type=ApprovalConditionType.THRESHOLD,
                value={"field": "amount", "threshold": 1000}
            ),
            approvalType=ApprovalType.EXPLICIT
        ),
        ApprovalRule(
            name="External communication",
            description="Always require approval for external emails",
            condition=ApprovalCondition(
                type=ApprovalConditionType.CATEGORY,
                value={"category": "external_communication"}
            ),
            approvalType=ApprovalType.EXPLICIT
        )
    ]
)
```

#### Agent-Specific Constraints

```python
from models.agent import AgentConstraint, ConstraintType, ConstraintSource

agent_constraints = [
    AgentConstraint(
        type=ConstraintType.ACTION_FORBIDDEN,
        description="Cannot access production database",
        condition="target.environment == 'production'",
        isActive=True,
        source=ConstraintSource.SYSTEM
    ),
    AgentConstraint(
        type=ConstraintType.APPROVAL_REQUIRED,
        description="All Slack messages require approval",
        condition="mcp_service == 'slack' AND operation == 'send'",
        isActive=True,
        source=ConstraintSource.USER
    ),
    AgentConstraint(
        type=ConstraintType.TIME_RESTRICTION,
        description="Only operate during business hours",
        condition="hour >= 9 AND hour <= 17",
        isActive=True,
        source=ConstraintSource.USER
    )
]
```

---

## 10. Troubleshooting

### 10.1 WebSocket Connection Issues

**Problem:** Frontend cannot connect to WebSocket server

**Symptoms:**
```
[WebSocket] Connection failed: Error: ...
```

**Solutions:**

1. **Check Backend Running:**
```bash
# Backend should be running on port 8080
python server_python/main.py
# Look for: "WebSocket server running on port 8080"
```

2. **Verify Port Availability:**
```bash
# Check if port 8080 is in use
lsof -i :8080  # macOS/Linux
netstat -ano | findstr :8080  # Windows
```

3. **Check Firewall:**
Ensure port 8080 is not blocked by firewall.

4. **Update Frontend WebSocket URL:**
```typescript
// src/App.tsx
const ws = new WebSocket('ws://localhost:8080');
// Ensure this matches backend WS_PORT in .env
```

### 10.2 Slack Webhook Not Receiving Events

**Problem:** Slack events not creating tasks

**Symptoms:**
- No tasks appear when mentioning bot in Slack
- Backend not logging event reception
- Webhook endpoint returns errors

**Solutions:**

1. **Verify ngrok Running:**
```bash
ngrok http 8000
# Ensure forwarding URL matches Slack configuration
# Important: URL must include /api/slack/webhook path
```

2. **Check Slack Event Subscriptions:**
- Go to Slack App settings → Event Subscriptions
- Verify Request URL: `https://your-ngrok-url/api/slack/webhook`
- Check "Verified" badge appears (green checkmark)
- If not verified, check backend logs for URL verification errors

3. **Validate Environment Variables:**
```bash
# server_python/.env
SLACK_BOT_TOKEN=xoxb-...  # Should start with xoxb-
SLACK_SIGNING_SECRET=...  # Required for signature verification
HTTP_PORT=8000
WS_PORT=8080
```

4. **Check Backend Logs:**
```bash
python main.py
# Look for detailed logs:
# [SlackWebhook] New request received
# [SlackWebhook] Headers: {...}
# [SlackWebhookService] Processing event type: event_callback
# [SlackWebhookService] Handling event type: app_mention
# [SlackWebhookService] Created task: ...
# [Server] Task created from Slack: ...
# [WebSocket] Broadcasting task_created: ...
```

5. **Test Webhook Manually:**
```bash
# URL verification test
curl -X POST http://localhost:8000/api/slack/webhook \
  -H "Content-Type: application/json" \
  -d '{"type":"url_verification","challenge":"test123"}'
# Should return: {"challenge":"test123"}

# Event callback test (requires valid signature in production)
curl -X POST http://localhost:8000/api/slack/webhook \
  -H "Content-Type: application/json" \
  -H "X-Slack-Signature: v0=..." \
  -H "X-Slack-Request-Timestamp: 1234567890" \
  -d '{"type":"event_callback","event":{"type":"app_mention","text":"test","user":"U123","channel":"C123","ts":"1234567890.123456"}}'
```

6. **Common Issues and Fixes:**

**Issue: "Slack webhook service not initialized"**
- **Cause:** Service not properly initialized in main.py
- **Fix:** Ensure `slack_webhook_service` is created before router registration

**Issue: "Invalid signature"**
- **Cause:** Signing secret mismatch or missing
- **Fix:** 
  - Verify `SLACK_SIGNING_SECRET` in `.env` matches Slack app settings
  - Check that signature verification is working (logs will show "Signature verified successfully")

**Issue: Events received but no tasks created**
- **Cause:** Event type not handled or empty text after cleaning
- **Fix:**
  - Check backend logs for "Event type X not handled" messages
  - Verify event structure matches expected format
  - Ensure message text is not empty after mention removal

**Issue: URL verification fails**
- **Cause:** Challenge response not returned correctly
- **Fix:**
  - Verify endpoint returns `{"challenge": "<challenge_value>}` for URL verification
  - Check that URL verification happens before signature verification

7. **Debug Mode:**
The code now includes extensive logging. Check console output for:
- Request headers and body
- Event type and structure
- Task creation details
- Handler execution status
- Any error messages with stack traces

### 10.3 Agent Not Processing Assigned Tasks

**Problem:** Agent receives task assignment but doesn't process it

**Symptoms:**
- Task assigned to agent but no tickets or approvals created
- Agent status doesn't change
- No processing logs in console
- Auto-assigned tasks don't start processing

**Solutions:**

1. **Check Auto-Assignment WebSocket Message:**
```typescript
// Frontend should send assign_task message when auto-assigning
[App] Auto-assigned and sent assign_task message: { type: 'assign_task', ... }
```

2. **Verify Backend Receives Message:**
```python
# Backend logs should show:
[Server] Client action from {client_id}: assign_task
[Server] Assigning task {task_id} to agent {agent_id}
[Server] Initializing agent {agent_id}
[Server] Starting task processing for agent {name}
```

3. **Check Agent Initialization:**
```python
# Backend logs should show:
[Server] Initializing agent {agent_id}
[Server] Agent {agent_id} initialized and started
```

2. **Verify Agent Process Method:**
```python
# Check that agent.process() is being called
[Server] Starting task processing for agent {name}
[DemoAgent {name}] Processing task: {task_id}
```

3. **Check Result Processing:**
```python
# Results should be processed and broadcast
[Server] Agent {name} completed task processing
[Server] Result: X tickets, Y approvals
[Server] Broadcasting ticket_created: {ticket_id}
[Server] Broadcasting approval_request: {approval_id}
```

4. **Verify Event Handlers:**
- Ensure `handle_agent_event` is registered in main.py
- Check that `ticket_created` and `approval_requested` events are handled
- Verify WebSocket broadcasts are working

5. **Common Issues:**

**Issue: Agent not initialized**
- **Cause:** Agent created but `initialize()` and `start()` not called
- **Fix:** Ensure agent initialization happens before task assignment

**Issue: Results not broadcast**
- **Cause:** `process_agent_task()` doesn't extract and broadcast results
- **Fix:** Check that tickets and approvals are extracted from result and broadcast

**Issue: Agent state not updated**
- **Cause:** `currentTaskId` and `currentTaskDescription` not set
- **Fix:** Ensure agent state is updated before and after processing

### 10.4 Task Auto-Assignment Not Working

**Problem:** Tasks remain unassigned despite auto-assign settings

**Symptoms:**
- Tasks created but `assignedAgentId` is null
- No orchestration logs in console

**Solutions:**

1. **Check Auto-Assign Mode:**
```typescript
// Verify in TaskPanel
autoAssignMode: 'global' | 'manual'
```

2. **Verify Agent Availability:**
```typescript
// Check that agents exist and are active
console.log('Available agents:', allAgents);
console.log('Active agents:', allAgents.filter(a => a.isActive));
```

3. **Check Task Auto-Assign Flag:**
```typescript
// For manual mode, task must have autoAssign: true
// or meet default criteria (high priority, Slack source)
```

4. **Verify LLM Configuration:**
```typescript
// App.tsx
orchestrationServiceRef.current = new OrchestrationService(settings.llmConfig);
// Ensure llmConfig has valid API key
```

5. **Check Console for Orchestration Errors:**
```
[Orchestration] Error selecting agent: ...
```

### 10.4 Approval Requests Not Appearing

**Problem:** Approval queue empty despite agent operations

**Symptoms:**
- Tickets created but no approval requests
- Operations pending indefinitely

**Solutions:**

1. **Verify Ticket Requires Approval:**
```python
ticket = Ticket(
    requiresApproval=True,  # Must be True
    # ...
)
```

2. **Check Approval Event Emission:**
```python
# In agent code
self.emit(AgentEvent(
    type=AgentEventType.APPROVAL_REQUESTED,
    payload=approval_request
))
```

3. **Verify WebSocket Broadcast:**
```python
# main.py event handler
def handle_agent_event(event):
    if event.type == "approval_requested":
        ws_server.broadcast_approval_request(approval)
```

4. **Check Frontend Approval Handler:**
```typescript
// useWebSocket.ts
case 'approval_request':
  setApprovalQueue(prev => [...prev, message.payload as ApprovalRequest]);
  break;
```

### 10.5 MCP Service Connection Failures

**Problem:** MCP services fail to connect

**Symptoms:**
```
[NotionService] Connection failed: API key required
```

**Solutions:**

1. **Verify API Credentials:**
```bash
# .env file
NOTION_API_KEY=your_key_here
GMAIL_CLIENT_ID=your_id
SLACK_BOT_TOKEN=xoxb-...
```

2. **Check Service Registration:**
```python
# main.py
mcp_registry.register(notion_service, config)
await mcp_registry.connect("notion")  # Ensure this is called
```

3. **Validate Service Status:**
```python
status = mcp_registry.get_status()
print(status)
# Should show: {"total": 4, "connected": 3, "disconnected": 1}
```

4. **Check Service-Specific Requirements:**

**Notion:**
- API key must have proper workspace access
- Check permissions at notion.so/my-integrations

**Gmail:**
- OAuth2 credentials configured
- Redirect URI matches application

**Slack:**
- Bot token starts with `xoxb-`
- Bot has required scopes

### 10.6 Agent State Machine Errors

**Problem:** Agent stuck in invalid state

**Symptoms:**
```
[Agent] Invalid state transition from 'exploring' to 'idle'
```

**Solutions:**

1. **Check Valid Transitions:**
```python
# Only these transitions allowed:
# idle → exploring (START_TASK)
# exploring → structuring (INFO_COLLECTED)
# exploring → idle (NO_ACTION_NEEDED)
# structuring → validating (STRUCTURE_COMPLETE)
# validating → summarizing (VALIDATION_PASSED)
# validating → idle (VALIDATION_FAILED)
# summarizing → idle (TASK_COMPLETE)
```

2. **Reset Agent State:**
```python
await agent.stop()  # Resets to idle
await agent.start()  # Restart
```

3. **Check Error Handling:**
```python
# Ensure try-except in agent.process()
try:
    await self.process(input)
except Exception as error:
    self.state_machine.reset()  # Return to idle
    raise
```

### 10.7 Python Dependency Issues

**Problem:** Import errors or missing modules

**Symptoms:**
```
ModuleNotFoundError: No module named 'fastapi'
```

**Solutions:**

1. **Reinstall Dependencies:**
```bash
cd server_python
pip install -r requirements.txt
```

2. **Check Python Version:**
```bash
python --version
# Should be 3.9 or higher
```

3. **Use Virtual Environment:**
```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

4. **Verify Installed Packages:**
```bash
pip list
# Should include: fastapi, uvicorn, websockets, pydantic
```

### 10.8 Frontend Build Errors

**Problem:** `npm run build` fails

**Symptoms:**
```
Error: Cannot find module '@vitejs/plugin-react'
```

**Solutions:**

1. **Reinstall Node Modules:**
```bash
rm -rf node_modules package-lock.json
npm install
```

2. **Check Node Version:**
```bash
node --version
# Should be 18.x or higher
```

3. **Clear Vite Cache:**
```bash
rm -rf node_modules/.vite
npm run dev
```

4. **Check TypeScript Errors:**
```bash
npm run lint
# Fix any reported errors
```

### 10.9 Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `WebSocket connection failed` | Backend not running | Start `python main.py` |
| `Agent not found: {id}` | Agent unregistered | Check agent_registry.get_all_agents() |
| `Service not connected` | MCP service disconnected | Call mcp_registry.connect(type) |
| `Operation requires approval` | Approval not received | Check approval status |
| `Invalid transition` | State machine violation | Reset agent state |
| `Signature verification failed` | Wrong Slack secret | Update SLACK_SIGNING_SECRET |
| `Challenge validation failed` | ngrok URL mismatch | Update Slack event URL |

### 10.10 Debugging Tips

**Enable Verbose Logging:**

```python
# main.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Monitor WebSocket Messages:**

```typescript
// useWebSocket.ts
ws.onmessage = (event) => {
  console.log('[WS Received]', event.data);  // Add this
  const message = JSON.parse(event.data);
  handleMessage(message);
};
```

**Check Backend Health:**

```bash
# WebSocket server should log:
[WebSocket] Server started on port 8080
[WebSocket] Client connected: {id}

# HTTP server should log:
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Verify Data Flow:**

```python
# Add logging in event handlers
def handle_task_created(task: Task):
    print(f"[DEBUG] Task created: {task.id} - {task.title}")
    ws_server.broadcast_task_created(task)
```

---

## Appendix A: Quick Reference

### Environment Variables

```bash
# Server
WS_PORT=8080
HTTP_PORT=8000

# Integrations
NOTION_API_KEY=
SLACK_BOT_TOKEN=
SLACK_SIGNING_SECRET=
SLACK_WEBHOOK_URL=
GMAIL_CLIENT_ID=
GMAIL_CLIENT_SECRET=
CONFLUENCE_URL=
CONFLUENCE_USERNAME=
CONFLUENCE_API_TOKEN=

# LLM
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
```

### Command Cheat Sheet

```bash
# Frontend
npm install        # Install dependencies
npm run dev        # Start dev server
npm run build      # Production build
npm run lint       # Check code quality

# Backend
pip install -r requirements.txt  # Install dependencies
python main.py                   # Start server
python -m pytest                 # Run tests (if available)

# ngrok (for Slack)
ngrok http 8000    # Expose local server
```

### Key File Locations

| File | Purpose |
|------|---------|
| `src/App.tsx` | Main React app |
| `src/hooks/useWebSocket.ts` | WebSocket hook |
| `src/services/orchestration.ts` | Task assignment |
| `server_python/main.py` | Backend entry point |
| `server_python/agents/base_agent.py` | Agent base class |
| `server_python/websocket/websocket_server.py` | WebSocket server |
| `server_python/services/slack_webhook.py` | Slack integration |
| `server_python/.env` | Environment config |

---

## Appendix B: Architecture Diagrams

### Agent Processing Pipeline

```
Input → [EXPLORE] → Decision Point
                         ├─ No Action Needed → Return Empty
                         └─ Proceed
                              ↓
                         [STRUCTURE]
                              ↓
                         [VALIDATE]
                              ├─ Invalid → Return Empty
                              └─ Valid
                                   ↓
                              [SUMMARIZE]
                                   ↓
                              Create Tickets & Approvals
                                   ↓
                              Return AgentOutput
```

### Task Lifecycle

```
Created → Pending → Assigned → In Progress → Completed
              ↓                      ↓
            Manual              Agent Working
           Assignment                ↓
                              Ticket Creation
                                     ↓
                              Approval Needed?
                              ├─ Yes → Wait for Approval
                              └─ No  → Execute
                                        ↓
                                    Complete
```

### WebSocket Message Flow

```
Backend Event
     ↓
Event Handler
     ↓
WebSocket Server
     ↓
broadcast_*()
     ↓
JSON Serialization
     ↓
Send to All Clients
     ↓
Frontend useWebSocket
     ↓
handleMessage()
     ↓
Update State
     ↓
React Re-render
```

---

*This documentation is accurate as of December 24, 2025. For the latest updates, check the project repository.*
