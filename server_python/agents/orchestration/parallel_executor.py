#!/usr/bin/env python3
"""
Parallel Executor - 병렬 Agent 실행

독립적인 Agent들을 병렬로 실행하여 성능을 향상시킵니다.
"""

import asyncio
from typing import List, Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass
from datetime import datetime

from .types import AgentStep, DynamicWorkflow
from ..agent_result import AgentResult, AgentLifecycleStatus


@dataclass
class ParallelExecutionResult:
    """병렬 실행 결과"""
    step_id: str
    agent_id: str
    agent_name: str
    result: AgentResult
    execution_time_ms: float
    error: Optional[str] = None


class ParallelExecutor:
    """
    병렬 Agent 실행기

    책임:
    - 독립적인 Agent들을 동시 실행
    - 타임아웃 관리
    - 결과 수집 및 정렬
    """

    def __init__(
        self,
        max_concurrency: int = 5,
        default_timeout: float = 60.0
    ):
        """
        Args:
            max_concurrency: 최대 동시 실행 수
            default_timeout: 기본 타임아웃 (초)
        """
        self._max_concurrency = max_concurrency
        self._default_timeout = default_timeout
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def execute_parallel(
        self,
        steps: List[AgentStep],
        executor_func: Callable[[AgentStep], Awaitable[AgentResult]],
        timeout: Optional[float] = None
    ) -> List[ParallelExecutionResult]:
        """
        여러 Agent 스텝을 병렬 실행

        Args:
            steps: 실행할 스텝 목록
            executor_func: 각 스텝을 실행할 함수
            timeout: 타임아웃 (초)

        Returns:
            실행 결과 목록
        """
        timeout = timeout or self._default_timeout

        tasks = [
            self._execute_with_semaphore(step, executor_func, timeout)
            for step in steps
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        return self._process_results(steps, results)

    async def _execute_with_semaphore(
        self,
        step: AgentStep,
        executor_func: Callable[[AgentStep], Awaitable[AgentResult]],
        timeout: float
    ) -> ParallelExecutionResult:
        """세마포어를 사용한 단일 실행"""
        start_time = datetime.now()

        async with self._semaphore:
            try:
                result = await asyncio.wait_for(
                    executor_func(step),
                    timeout=timeout
                )
                execution_time = (datetime.now() - start_time).total_seconds() * 1000

                return ParallelExecutionResult(
                    step_id=step.id,
                    agent_id=step.agent_id,
                    agent_name=step.agent_name,
                    result=result,
                    execution_time_ms=execution_time
                )

            except asyncio.TimeoutError:
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                return ParallelExecutionResult(
                    step_id=step.id,
                    agent_id=step.agent_id,
                    agent_name=step.agent_name,
                    result=AgentResult(
                        status=AgentLifecycleStatus.FAILED,
                        message="Execution timed out",
                        error={"code": "TIMEOUT", "message": f"Timeout after {timeout}s"}
                    ),
                    execution_time_ms=execution_time,
                    error="TIMEOUT"
                )

            except Exception as e:
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                return ParallelExecutionResult(
                    step_id=step.id,
                    agent_id=step.agent_id,
                    agent_name=step.agent_name,
                    result=AgentResult(
                        status=AgentLifecycleStatus.FAILED,
                        message=str(e),
                        error={"code": "EXECUTION_ERROR", "message": str(e)}
                    ),
                    execution_time_ms=execution_time,
                    error=str(e)
                )

    def _process_results(
        self,
        steps: List[AgentStep],
        results: List[Any]
    ) -> List[ParallelExecutionResult]:
        """결과 처리 및 정렬"""
        processed = []

        for i, result in enumerate(results):
            if isinstance(result, ParallelExecutionResult):
                processed.append(result)
            elif isinstance(result, Exception):
                # gather에서 예외가 발생한 경우
                step = steps[i]
                processed.append(ParallelExecutionResult(
                    step_id=step.id,
                    agent_id=step.agent_id,
                    agent_name=step.agent_name,
                    result=AgentResult(
                        status=AgentLifecycleStatus.FAILED,
                        message=str(result),
                        error={"code": "EXCEPTION", "message": str(result)}
                    ),
                    execution_time_ms=0,
                    error=str(result)
                ))

        # 원래 순서대로 정렬
        step_order = {step.id: i for i, step in enumerate(steps)}
        processed.sort(key=lambda r: step_order.get(r.step_id, 999))

        return processed

    @staticmethod
    def find_parallel_groups(steps: List[AgentStep]) -> List[List[AgentStep]]:
        """
        병렬 실행 가능한 그룹 찾기

        독립적인 스텝들을 그룹화하여 병렬 실행 가능한 단위로 분리합니다.
        현재는 순서(order)가 같은 스텝들을 병렬 실행 그룹으로 처리합니다.

        Args:
            steps: 스텝 목록

        Returns:
            병렬 실행 그룹 목록
        """
        if not steps:
            return []

        # order로 그룹화
        groups: Dict[int, List[AgentStep]] = {}
        for step in steps:
            order = step.order
            if order not in groups:
                groups[order] = []
            groups[order].append(step)

        # 순서대로 정렬하여 반환
        return [groups[order] for order in sorted(groups.keys())]

    @staticmethod
    def can_parallelize(step1: AgentStep, step2: AgentStep) -> bool:
        """
        두 스텝이 병렬 실행 가능한지 확인

        Args:
            step1: 첫 번째 스텝
            step2: 두 번째 스텝

        Returns:
            병렬 실행 가능 여부
        """
        # 같은 Agent는 병렬 실행 불가
        if step1.agent_id == step2.agent_id:
            return False

        # 같은 order면 병렬 실행 가능
        if step1.order == step2.order:
            return True

        # 의존성이 없으면 병렬 실행 가능 (향후 의존성 그래프 분석 추가)
        return False


class ParallelWorkflowExecutor:
    """
    병렬 워크플로우 실행기

    워크플로우 내에서 병렬 실행 가능한 스텝들을 자동 감지하고 실행합니다.
    """

    def __init__(
        self,
        parallel_executor: Optional[ParallelExecutor] = None,
        enable_parallel: bool = True
    ):
        """
        Args:
            parallel_executor: ParallelExecutor 인스턴스
            enable_parallel: 병렬 실행 활성화 여부
        """
        self._parallel_executor = parallel_executor or ParallelExecutor()
        self._enable_parallel = enable_parallel

    async def execute_workflow_steps(
        self,
        workflow: DynamicWorkflow,
        executor_func: Callable[[AgentStep], Awaitable[AgentResult]]
    ) -> List[ParallelExecutionResult]:
        """
        워크플로우 스텝들 실행

        병렬 실행이 가능한 스텝들은 동시에 실행합니다.

        Args:
            workflow: 워크플로우
            executor_func: 스텝 실행 함수

        Returns:
            실행 결과 목록
        """
        if not self._enable_parallel:
            # 순차 실행
            return await self._execute_sequential(workflow.steps, executor_func)

        # 병렬 그룹 찾기
        groups = ParallelExecutor.find_parallel_groups(workflow.steps)
        all_results = []

        for group in groups:
            if len(group) == 1:
                # 단일 스텝은 그냥 실행
                result = await executor_func(group[0])
                all_results.append(ParallelExecutionResult(
                    step_id=group[0].id,
                    agent_id=group[0].agent_id,
                    agent_name=group[0].agent_name,
                    result=result,
                    execution_time_ms=0
                ))
            else:
                # 여러 스텝은 병렬 실행
                results = await self._parallel_executor.execute_parallel(
                    group, executor_func
                )
                all_results.extend(results)

            # 실패한 스텝이 있으면 중단
            for result in all_results:
                if result.result.status == AgentLifecycleStatus.FAILED:
                    print(f"[ParallelWorkflowExecutor] Step failed: {result.agent_name}")
                    return all_results

        return all_results

    async def _execute_sequential(
        self,
        steps: List[AgentStep],
        executor_func: Callable[[AgentStep], Awaitable[AgentResult]]
    ) -> List[ParallelExecutionResult]:
        """순차 실행"""
        results = []
        for step in steps:
            start_time = datetime.now()
            result = await executor_func(step)
            execution_time = (datetime.now() - start_time).total_seconds() * 1000

            results.append(ParallelExecutionResult(
                step_id=step.id,
                agent_id=step.agent_id,
                agent_name=step.agent_name,
                result=result,
                execution_time_ms=execution_time
            ))

            if result.status == AgentLifecycleStatus.FAILED:
                break

        return results
