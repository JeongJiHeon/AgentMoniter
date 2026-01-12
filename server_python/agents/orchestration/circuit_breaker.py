#!/usr/bin/env python3
"""
Circuit Breaker - 에러 복구 메커니즘

Agent 실패 시 자동 복구 및 Fallback 처리를 담당합니다.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum


class CircuitState(str, Enum):
    """Circuit 상태"""
    CLOSED = "closed"      # 정상 동작
    OPEN = "open"          # 차단됨 (실패 임계치 초과)
    HALF_OPEN = "half_open"  # 테스트 중


@dataclass
class CircuitStats:
    """Circuit 통계"""
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    total_calls: int = 0


@dataclass
class CircuitConfig:
    """Circuit Breaker 설정"""
    failure_threshold: int = 3          # 실패 임계치
    success_threshold: int = 2          # 복구를 위한 성공 횟수
    timeout_seconds: int = 30           # OPEN 상태 유지 시간
    half_open_max_calls: int = 3        # HALF_OPEN에서 허용할 최대 호출 수


class CircuitBreaker:
    """
    Circuit Breaker 패턴 구현

    책임:
    - Agent 호출 실패 추적
    - 실패 임계치 초과 시 차단
    - 자동 복구 시도
    """

    def __init__(self, config: Optional[CircuitConfig] = None):
        """
        Args:
            config: Circuit Breaker 설정
        """
        self._config = config or CircuitConfig()
        self._circuits: Dict[str, CircuitState] = {}
        self._stats: Dict[str, CircuitStats] = {}
        self._half_open_calls: Dict[str, int] = {}

    def get_state(self, agent_id: str) -> CircuitState:
        """Agent의 Circuit 상태 조회"""
        if agent_id not in self._circuits:
            self._circuits[agent_id] = CircuitState.CLOSED
            self._stats[agent_id] = CircuitStats()
        return self._circuits[agent_id]

    def get_stats(self, agent_id: str) -> CircuitStats:
        """Agent의 통계 조회"""
        if agent_id not in self._stats:
            self._stats[agent_id] = CircuitStats()
        return self._stats[agent_id]

    async def call(
        self,
        agent_id: str,
        func: Callable[..., Awaitable[Any]],
        *args,
        fallback: Optional[Callable[..., Awaitable[Any]]] = None,
        **kwargs
    ) -> Any:
        """
        Circuit Breaker를 통한 함수 호출

        Args:
            agent_id: Agent ID
            func: 호출할 함수
            *args: 함수 인자
            fallback: 실패 시 대체 함수
            **kwargs: 함수 키워드 인자

        Returns:
            함수 실행 결과

        Raises:
            CircuitOpenError: Circuit이 OPEN 상태일 때
        """
        state = self.get_state(agent_id)
        stats = self.get_stats(agent_id)

        # OPEN 상태 체크
        if state == CircuitState.OPEN:
            if self._should_attempt_reset(agent_id):
                self._transition_to_half_open(agent_id)
            else:
                if fallback:
                    return await fallback(*args, **kwargs)
                raise CircuitOpenError(f"Circuit is OPEN for agent: {agent_id}")

        # HALF_OPEN 상태에서 호출 제한
        if state == CircuitState.HALF_OPEN:
            if self._half_open_calls.get(agent_id, 0) >= self._config.half_open_max_calls:
                if fallback:
                    return await fallback(*args, **kwargs)
                raise CircuitOpenError(f"Circuit is HALF_OPEN and max calls reached for: {agent_id}")
            self._half_open_calls[agent_id] = self._half_open_calls.get(agent_id, 0) + 1

        # 함수 호출
        stats.total_calls += 1
        try:
            result = await func(*args, **kwargs)
            self._on_success(agent_id)
            return result
        except Exception as e:
            self._on_failure(agent_id)
            if fallback:
                return await fallback(*args, **kwargs)
            raise

    def _should_attempt_reset(self, agent_id: str) -> bool:
        """OPEN 상태에서 HALF_OPEN으로 전환 시도 여부"""
        stats = self._stats.get(agent_id)
        if not stats or not stats.last_failure_time:
            return True

        timeout = timedelta(seconds=self._config.timeout_seconds)
        return datetime.now() - stats.last_failure_time > timeout

    def _transition_to_half_open(self, agent_id: str) -> None:
        """HALF_OPEN 상태로 전환"""
        self._circuits[agent_id] = CircuitState.HALF_OPEN
        self._half_open_calls[agent_id] = 0
        print(f"[CircuitBreaker] {agent_id}: OPEN → HALF_OPEN")

    def _on_success(self, agent_id: str) -> None:
        """성공 처리"""
        stats = self._stats[agent_id]
        stats.success_count += 1
        stats.last_success_time = datetime.now()

        state = self._circuits.get(agent_id, CircuitState.CLOSED)

        if state == CircuitState.HALF_OPEN:
            # HALF_OPEN에서 충분한 성공 시 CLOSED로 복구
            if stats.success_count >= self._config.success_threshold:
                self._circuits[agent_id] = CircuitState.CLOSED
                stats.failure_count = 0
                self._half_open_calls[agent_id] = 0
                print(f"[CircuitBreaker] {agent_id}: HALF_OPEN → CLOSED (recovered)")

    def _on_failure(self, agent_id: str) -> None:
        """실패 처리"""
        stats = self._stats[agent_id]
        stats.failure_count += 1
        stats.last_failure_time = datetime.now()
        stats.success_count = 0  # 연속 성공 카운트 리셋

        state = self._circuits.get(agent_id, CircuitState.CLOSED)

        if state == CircuitState.CLOSED:
            # 실패 임계치 초과 시 OPEN으로 전환
            if stats.failure_count >= self._config.failure_threshold:
                self._circuits[agent_id] = CircuitState.OPEN
                print(f"[CircuitBreaker] {agent_id}: CLOSED → OPEN (failures: {stats.failure_count})")

        elif state == CircuitState.HALF_OPEN:
            # HALF_OPEN에서 실패 시 다시 OPEN으로
            self._circuits[agent_id] = CircuitState.OPEN
            self._half_open_calls[agent_id] = 0
            print(f"[CircuitBreaker] {agent_id}: HALF_OPEN → OPEN (failed during test)")

    def reset(self, agent_id: str) -> None:
        """특정 Agent의 Circuit 리셋"""
        self._circuits[agent_id] = CircuitState.CLOSED
        self._stats[agent_id] = CircuitStats()
        self._half_open_calls.pop(agent_id, None)
        print(f"[CircuitBreaker] {agent_id}: Reset to CLOSED")

    def reset_all(self) -> None:
        """모든 Circuit 리셋"""
        self._circuits.clear()
        self._stats.clear()
        self._half_open_calls.clear()
        print("[CircuitBreaker] All circuits reset")

    def get_summary(self) -> Dict[str, Any]:
        """전체 Circuit 상태 요약"""
        return {
            agent_id: {
                "state": state.value,
                "stats": {
                    "failure_count": self._stats.get(agent_id, CircuitStats()).failure_count,
                    "success_count": self._stats.get(agent_id, CircuitStats()).success_count,
                    "total_calls": self._stats.get(agent_id, CircuitStats()).total_calls,
                }
            }
            for agent_id, state in self._circuits.items()
        }


class CircuitOpenError(Exception):
    """Circuit이 OPEN 상태일 때 발생하는 예외"""
    pass


# 전역 Circuit Breaker 인스턴스
circuit_breaker = CircuitBreaker()
