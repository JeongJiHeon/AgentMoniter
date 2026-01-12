"""
Pytest Configuration and Fixtures

테스트 전역 설정 및 공유 fixtures입니다.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock
from typing import Generator

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """테스트 세션용 이벤트 루프"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_ws_server() -> MagicMock:
    """WebSocket 서버 모킹"""
    ws_server = MagicMock()
    ws_server.broadcast_notification = MagicMock()
    ws_server.broadcast_agent_update = MagicMock()
    ws_server.broadcast_agent_log = MagicMock()
    ws_server.broadcast_task_interaction = MagicMock()
    ws_server.broadcast_chat_message = MagicMock()
    ws_server.broadcast_message = MagicMock()
    return ws_server


@pytest.fixture
def mock_agent_registry() -> MagicMock:
    """Agent 레지스트리 모킹"""
    registry = MagicMock()
    registry.get_agent = MagicMock(return_value=None)
    registry.get_all_agents = MagicMock(return_value=[])
    registry.register_agent = MagicMock()
    return registry


@pytest.fixture
def sample_agent_config() -> dict:
    """샘플 Agent 설정"""
    return {
        "name": "Test Agent",
        "type": "custom",
        "description": "Test agent for unit tests",
        "constraints": [],
        "permissions": {},
        "custom_config": {}
    }


@pytest.fixture
def sample_task_payload() -> dict:
    """샘플 Task 페이로드"""
    return {
        "taskId": "test-task-123",
        "agentId": "test-agent-456",
        "task": {
            "title": "Test Task",
            "description": "This is a test task",
            "priority": "medium",
            "source": "manual"
        },
        "orchestrationPlan": {
            "agents": [],
            "needsUserInput": False,
            "inputPrompt": ""
        }
    }


@pytest.fixture
def sample_approval_payload() -> dict:
    """샘플 승인 페이로드"""
    return {
        "requestId": "req-123",
        "ticketId": "ticket-456",
        "agentId": "agent-789"
    }


@pytest.fixture
def mock_agent() -> MagicMock:
    """Agent 인스턴스 모킹"""
    agent = MagicMock()
    agent.id = "test-agent-id"
    agent.name = "Test Agent"
    agent.type = "custom"
    agent.get_state = MagicMock(return_value=MagicMock(
        id="test-agent-id",
        name="Test Agent",
        type="custom",
        status="IDLE"
    ))
    agent.initialize = AsyncMock()
    agent.start = AsyncMock()
    agent.on_approval_received = AsyncMock()
    agent._emit_state_change = MagicMock()
    return agent


@pytest.fixture
def mock_dynamic_orchestration() -> MagicMock:
    """Dynamic Orchestration 모킹"""
    orchestration = MagicMock()
    orchestration.has_pending_workflow = MagicMock(return_value=False)
    orchestration.set_ws_server = MagicMock()
    orchestration.resume_with_user_input = AsyncMock(return_value=None)
    orchestration.get_workflow = MagicMock(return_value=None)
    orchestration.remove_workflow = MagicMock()
    return orchestration


# =============================================================================
# Orchestration Module Fixtures
# =============================================================================

@pytest.fixture
def sample_workflow_steps() -> list:
    """샘플 워크플로우 스텝"""
    from agents.orchestration.types import AgentStep, AgentRole

    return [
        AgentStep(
            agent_id="agent-1",
            agent_name="Information Gatherer",
            role=AgentRole.WORKER,
            order=1,
            depends_on=[]
        ),
        AgentStep(
            agent_id="agent-2",
            agent_name="Q&A Handler",
            role=AgentRole.Q_AND_A,
            order=2,
            depends_on=["agent-1"]
        ),
        AgentStep(
            agent_id="agent-3",
            agent_name="Executor",
            role=AgentRole.WORKER,
            order=3,
            depends_on=["agent-2"]
        )
    ]


@pytest.fixture
def sample_workflow(sample_workflow_steps) -> 'DynamicWorkflow':
    """샘플 워크플로우"""
    from agents.orchestration.types import DynamicWorkflow, WorkflowPhase

    return DynamicWorkflow(
        task_id="test-task-123",
        original_request="테스트 요청입니다",
        created_at=datetime.now(),
        steps=sample_workflow_steps,
        current_step_index=0,
        phase=WorkflowPhase.ANALYZING,
        context={},
        collected_facts={},
        user_decisions={},
        qa_history=[]
    )


@pytest.fixture
def mock_repository() -> MagicMock:
    """Repository 모킹"""
    repo = MagicMock()
    repo.save = AsyncMock(return_value=True)
    repo.load = AsyncMock(return_value=None)
    repo.delete = AsyncMock(return_value=True)
    repo.exists = AsyncMock(return_value=False)
    repo.list_all = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_metrics_collector() -> MagicMock:
    """MetricsCollector 모킹"""
    collector = MagicMock()
    collector.increment = MagicMock()
    collector.observe = MagicMock()
    collector.set_gauge = MagicMock()
    collector.record_agent_execution = MagicMock()
    collector.record_workflow_completion = MagicMock()
    collector.start_timer = MagicMock(return_value="timer-id")
    collector.stop_timer = MagicMock(return_value=100.0)
    return collector


@pytest.fixture
def mock_circuit_breaker() -> MagicMock:
    """CircuitBreaker 모킹"""
    cb = MagicMock()
    cb.call = AsyncMock()
    cb.get_state = MagicMock()
    cb.reset = MagicMock()
    return cb


@pytest.fixture
def mock_llm_response() -> str:
    """샘플 LLM 응답"""
    import json
    return json.dumps({
        "task_type": "lunch_booking",
        "confidence": 0.9,
        "reasoning": "음식 관련 요청",
        "extracted_entities": {
            "location": "강남역",
            "party_size": 4
        }
    })
