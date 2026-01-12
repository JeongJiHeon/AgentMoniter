"""
Circuit Breaker Unit Tests

에러 복구 메커니즘(Circuit Breaker)의 단위 테스트입니다.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from agents.orchestration.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitConfig,
    CircuitOpenError,
)


class TestCircuitBreaker:
    """CircuitBreaker 테스트"""

    @pytest.fixture
    def circuit_breaker(self):
        """기본 설정의 CircuitBreaker 인스턴스"""
        config = CircuitConfig(
            failure_threshold=3,
            timeout_seconds=1,  # 테스트용 짧은 타임아웃
            half_open_max_calls=2
        )
        return CircuitBreaker(config)

    @pytest.mark.asyncio
    async def test_initial_state_is_closed(self, circuit_breaker):
        """초기 상태는 CLOSED"""
        state = circuit_breaker.get_state("test-agent")
        assert state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_successful_call_keeps_closed(self, circuit_breaker):
        """성공적인 호출은 CLOSED 상태 유지"""
        async def success_func():
            return "success"

        result = await circuit_breaker.call("test-agent", success_func)

        assert result == "success"
        assert circuit_breaker.get_state("test-agent") == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_failures_open_circuit(self, circuit_breaker):
        """실패가 threshold를 초과하면 OPEN 상태로 전환"""
        async def fail_func():
            raise Exception("Test failure")

        # threshold(3)번 실패
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call("test-agent", fail_func)

        assert circuit_breaker.get_state("test-agent") == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_open_circuit_raises_error(self, circuit_breaker):
        """OPEN 상태에서는 CircuitOpenError 발생"""
        async def fail_func():
            raise Exception("Test failure")

        # 회로 열기
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call("test-agent", fail_func)

        # OPEN 상태에서 호출 시도
        with pytest.raises(CircuitOpenError) as exc_info:
            await circuit_breaker.call("test-agent", fail_func)

        assert "test-agent" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_open_circuit_uses_fallback(self, circuit_breaker):
        """OPEN 상태에서 fallback 함수 사용"""
        async def fail_func():
            raise Exception("Test failure")

        async def fallback_func():
            return "fallback_result"

        # 회로 열기
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call("test-agent", fail_func)

        # fallback 사용
        result = await circuit_breaker.call(
            "test-agent",
            fail_func,
            fallback=fallback_func
        )

        assert result == "fallback_result"

    @pytest.mark.asyncio
    async def test_circuit_transitions_to_half_open(self, circuit_breaker):
        """recovery_timeout 후 HALF_OPEN 상태로 전환"""
        async def fail_func():
            raise Exception("Test failure")

        # 회로 열기
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call("test-agent", fail_func)

        assert circuit_breaker.get_state("test-agent") == CircuitState.OPEN

        # recovery_timeout 대기
        await asyncio.sleep(1.1)

        async def success_func():
            return "success"

        # 다음 호출에서 HALF_OPEN으로 전환 시도
        result = await circuit_breaker.call("test-agent", success_func)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_half_open_success_closes_circuit(self, circuit_breaker):
        """HALF_OPEN 상태에서 성공하면 CLOSED로 복구"""
        async def fail_func():
            raise Exception("Test failure")

        async def success_func():
            return "success"

        # 회로 열기
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call("test-agent", fail_func)

        # recovery_timeout 대기
        await asyncio.sleep(1.1)

        # 성공적인 호출
        await circuit_breaker.call("test-agent", success_func)
        await circuit_breaker.call("test-agent", success_func)

        assert circuit_breaker.get_state("test-agent") == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_failure_reopens_circuit(self, circuit_breaker):
        """HALF_OPEN 상태에서 실패하면 다시 OPEN으로 전환"""
        async def fail_func():
            raise Exception("Test failure")

        # 회로 열기
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call("test-agent", fail_func)

        # recovery_timeout 대기
        await asyncio.sleep(1.1)

        # HALF_OPEN 상태에서 실패
        with pytest.raises(Exception):
            await circuit_breaker.call("test-agent", fail_func)

        assert circuit_breaker.get_state("test-agent") == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_independent_circuits_per_agent(self, circuit_breaker):
        """각 Agent별로 독립적인 회로 상태"""
        async def fail_func():
            raise Exception("Test failure")

        async def success_func():
            return "success"

        # agent-1 회로 열기
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call("agent-1", fail_func)

        # agent-1은 OPEN, agent-2는 CLOSED
        assert circuit_breaker.get_state("agent-1") == CircuitState.OPEN
        assert circuit_breaker.get_state("agent-2") == CircuitState.CLOSED

        # agent-2는 정상 동작
        result = await circuit_breaker.call("agent-2", success_func)
        assert result == "success"

    @pytest.mark.asyncio
    async def test_reset_circuit(self, circuit_breaker):
        """회로 수동 리셋"""
        async def fail_func():
            raise Exception("Test failure")

        # 회로 열기
        for _ in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call("test-agent", fail_func)

        assert circuit_breaker.get_state("test-agent") == CircuitState.OPEN

        # 수동 리셋
        circuit_breaker.reset("test-agent")

        assert circuit_breaker.get_state("test-agent") == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_get_stats(self, circuit_breaker):
        """개별 통계 조회"""
        async def success_func():
            return "success"

        async def fail_func():
            raise Exception("Test failure")

        # Agent 실행
        await circuit_breaker.call("agent-1", success_func)

        with pytest.raises(Exception):
            await circuit_breaker.call("agent-2", fail_func)

        stats_1 = circuit_breaker.get_stats("agent-1")
        stats_2 = circuit_breaker.get_stats("agent-2")

        # CircuitStats는 dataclass이므로 속성으로 접근
        assert stats_1.success_count == 1
        assert stats_1.failure_count == 0
        assert stats_2.success_count == 0
        assert stats_2.failure_count == 1
