"""
Parallel Executor Unit Tests

병렬 Agent 실행기의 단위 테스트입니다.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from uuid import uuid4

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from agents.orchestration.parallel_executor import (
    ParallelExecutor,
    ParallelExecutionResult,
)
from agents.orchestration.types import (
    AgentStep,
    AgentRole,
)
from agents.agent_result import completed, failed


def make_step(agent_id: str, agent_name: str, order: int = 1, description: str = "Test task") -> AgentStep:
    """테스트용 AgentStep 생성 헬퍼"""
    return AgentStep(
        id=str(uuid4()),
        agent_id=agent_id,
        agent_name=agent_name,
        agent_role=AgentRole.WORKER,
        description=description,
        order=order
    )


class TestParallelExecutor:
    """ParallelExecutor 테스트"""

    @pytest.fixture
    def executor(self):
        """기본 설정의 ParallelExecutor"""
        return ParallelExecutor(max_concurrency=3)

    @pytest.mark.asyncio
    async def test_execute_single_step(self, executor):
        """단일 스텝 실행"""
        step = make_step("agent-1", "Test Agent 1")

        async def executor_func(s):
            return completed(message="success")

        results = await executor.execute_parallel(
            steps=[step],
            executor_func=executor_func
        )

        assert len(results) == 1
        assert results[0].agent_id == "agent-1"

    @pytest.mark.asyncio
    async def test_execute_multiple_steps_parallel(self, executor):
        """다중 스텝 병렬 실행"""
        call_times = []

        steps = [
            make_step("agent-a", "Agent A"),
            make_step("agent-b", "Agent B"),
            make_step("agent-c", "Agent C")
        ]

        async def executor_func(step):
            call_times.append(asyncio.get_event_loop().time())
            await asyncio.sleep(0.05)
            return completed(message=f"result_{step.agent_id}")

        results = await executor.execute_parallel(
            steps=steps,
            executor_func=executor_func
        )

        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_respects_max_concurrency(self):
        """최대 동시 실행 제한 준수"""
        executor = ParallelExecutor(max_concurrency=2)
        concurrent_count = 0
        max_concurrent = 0

        steps = [make_step(f"agent-{i}", f"Agent {i}") for i in range(4)]

        async def executor_func(step):
            nonlocal concurrent_count, max_concurrent
            concurrent_count += 1
            max_concurrent = max(max_concurrent, concurrent_count)
            await asyncio.sleep(0.05)
            concurrent_count -= 1
            return completed(message=step.agent_id)

        results = await executor.execute_parallel(
            steps=steps,
            executor_func=executor_func
        )

        assert len(results) == 4
        assert max_concurrent <= 2

    @pytest.mark.asyncio
    async def test_handles_step_failure(self, executor):
        """스텝 실패 처리"""
        steps = [
            make_step("success-agent", "Success Agent"),
            make_step("fail-agent", "Fail Agent"),
            make_step("another-agent", "Another Agent")
        ]

        async def executor_func(step):
            if "fail" in step.agent_id:
                raise ValueError("Intentional failure")
            return completed(message=f"result_{step.agent_id}")

        results = await executor.execute_parallel(
            steps=steps,
            executor_func=executor_func
        )

        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_execution_time_tracking(self, executor):
        """실행 시간 추적"""
        step = make_step("agent-1", "Test Agent")

        async def executor_func(s):
            await asyncio.sleep(0.1)
            return completed(message="done")

        results = await executor.execute_parallel(
            steps=[step],
            executor_func=executor_func
        )

        assert results[0].execution_time_ms >= 100
        assert results[0].execution_time_ms < 300


class TestFindParallelGroups:
    """병렬 실행 가능한 그룹 찾기 테스트"""

    def test_empty_steps(self):
        """빈 스텝 리스트"""
        groups = ParallelExecutor.find_parallel_groups([])
        assert len(groups) == 0

    def test_single_step(self):
        """단일 스텝"""
        step = make_step("agent-1", "Agent 1")
        groups = ParallelExecutor.find_parallel_groups([step])
        assert len(groups) == 1
        assert len(groups[0]) == 1

    def test_multiple_independent_steps(self):
        """여러 독립 스텝"""
        steps = [
            make_step("agent-1", "Agent 1", order=1),
            make_step("agent-2", "Agent 2", order=1),
            make_step("agent-3", "Agent 3", order=1)
        ]
        groups = ParallelExecutor.find_parallel_groups(steps)

        # 같은 order면 병렬 실행 가능
        assert len(groups) >= 1
