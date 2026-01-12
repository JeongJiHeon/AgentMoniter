#!/usr/bin/env python3
"""
Orchestration Module - 리팩토링된 오케스트레이션 시스템

모듈 구성:
- legacy: 기존 오케스트레이션 (하위 호환성)
- types: 공통 타입 및 Enum
- workflow_manager: 워크플로우 생명주기 관리
- agent_executor: Worker Agent 실행
- qa_handler: Q&A Agent 처리
- final_narrator: 최종 응답 생성
- logger: 구조화된 로깅
- circuit_breaker: 에러 복구 메커니즘
- repository: 상태 영속성
- parallel_executor: 병렬 Agent 실행
- engine: 통합 오케스트레이션 엔진
"""

# =============================================================================
# Legacy exports (하위 호환성)
# =============================================================================
from .legacy import (
    call_llm,
    LLMClient,
    StepStatus,
    AgentContext,
    AgentResult as LegacyAgentResult,
    BaseAgent,
    LLMAgent,
    WorkflowStep,
    WorkflowState,
    WorkflowManager,  # Legacy WorkflowManager
    AgentRegistry,
    OrchestrationEngine,
    build_workflow_steps,
    workflow_manager,
    orchestration_engine,
)

# =============================================================================
# New modular exports
# =============================================================================
from .types import (
    AgentRole,
    WorkflowPhase,
    AgentStep,
    DynamicWorkflow,
    SYSTEM_AGENTS,
)

from .workflow_manager_v2 import WorkflowManager as WorkflowManagerV2

from .agent_executor import AgentExecutor

from .qa_handler import QAHandler

from .final_narrator import FinalNarrator

from .logger import (
    OrchestrationLogger,
    LogLevel,
    LogEntry,
    orchestration_logger,
)

from .circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitConfig,
    CircuitOpenError,
    circuit_breaker,
)

from .repository import (
    WorkflowRepository,
    InMemoryRepository,
    FileRepository,
    RedisRepository,
    create_repository,
)

from .parallel_executor import (
    ParallelExecutor,
    ParallelExecutionResult,
    ParallelWorkflowExecutor,
)

from .engine import OrchestrationEngineV2, orchestration_engine_v2

__all__ = [
    # Legacy (하위 호환성)
    'call_llm',
    'LLMClient',
    'StepStatus',
    'AgentContext',
    'LegacyAgentResult',
    'BaseAgent',
    'LLMAgent',
    'WorkflowStep',
    'WorkflowState',
    'WorkflowManager',  # Legacy
    'AgentRegistry',
    'OrchestrationEngine',
    'build_workflow_steps',
    'workflow_manager',
    'orchestration_engine',

    # Types
    'AgentRole',
    'WorkflowPhase',
    'AgentStep',
    'DynamicWorkflow',
    'SYSTEM_AGENTS',

    # Workflow Manager (new)
    'WorkflowManagerV2',

    # Agent Executor
    'AgentExecutor',

    # Q&A Handler
    'QAHandler',

    # Final Narrator
    'FinalNarrator',

    # Logger
    'OrchestrationLogger',
    'LogLevel',
    'LogEntry',
    'orchestration_logger',

    # Circuit Breaker
    'CircuitBreaker',
    'CircuitState',
    'CircuitConfig',
    'CircuitOpenError',
    'circuit_breaker',

    # Repository
    'WorkflowRepository',
    'InMemoryRepository',
    'FileRepository',
    'RedisRepository',
    'create_repository',

    # Parallel Executor
    'ParallelExecutor',
    'ParallelExecutionResult',
    'ParallelWorkflowExecutor',

    # Engine
    'OrchestrationEngineV2',
    'orchestration_engine_v2',
]
