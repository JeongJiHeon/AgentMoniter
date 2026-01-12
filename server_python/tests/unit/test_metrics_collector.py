"""
Metrics Collector Unit Tests

성능 메트릭 수집기의 단위 테스트입니다.
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from agents.metrics.collector import (
    MetricsCollector,
    MetricType,
    MetricEntry,
)


class TestMetricsCollectorCounters:
    """MetricsCollector Counter 메서드 테스트"""

    @pytest.fixture
    def collector(self):
        """MetricsCollector 인스턴스"""
        return MetricsCollector()

    def test_increment_counter(self, collector):
        """카운터 증가 테스트"""
        collector.increment("test_counter")
        assert collector.get_counter("test_counter") == 1.0

        collector.increment("test_counter", 5.0)
        assert collector.get_counter("test_counter") == 6.0

    def test_counter_with_labels(self, collector):
        """레이블을 포함한 카운터"""
        collector.increment("requests", labels={"method": "GET"})
        collector.increment("requests", labels={"method": "POST"})
        collector.increment("requests", labels={"method": "GET"}, value=2.0)

        assert collector.get_counter("requests", {"method": "GET"}) == 3.0
        assert collector.get_counter("requests", {"method": "POST"}) == 1.0

    def test_get_nonexistent_counter(self, collector):
        """존재하지 않는 카운터 조회"""
        assert collector.get_counter("nonexistent") == 0.0


class TestMetricsCollectorGauges:
    """MetricsCollector Gauge 메서드 테스트"""

    @pytest.fixture
    def collector(self):
        """MetricsCollector 인스턴스"""
        return MetricsCollector()

    def test_set_gauge(self, collector):
        """게이지 설정 테스트"""
        collector.set_gauge("active_connections", 10.0)
        assert collector.get_gauge("active_connections") == 10.0

        collector.set_gauge("active_connections", 5.0)
        assert collector.get_gauge("active_connections") == 5.0

    def test_gauge_with_labels(self, collector):
        """레이블을 포함한 게이지"""
        collector.set_gauge("memory_usage", 100.0, {"host": "server1"})
        collector.set_gauge("memory_usage", 200.0, {"host": "server2"})

        assert collector.get_gauge("memory_usage", {"host": "server1"}) == 100.0
        assert collector.get_gauge("memory_usage", {"host": "server2"}) == 200.0

    def test_get_nonexistent_gauge(self, collector):
        """존재하지 않는 게이지 조회"""
        assert collector.get_gauge("nonexistent") is None


class TestMetricsCollectorHistograms:
    """MetricsCollector Histogram 메서드 테스트"""

    @pytest.fixture
    def collector(self):
        """MetricsCollector 인스턴스"""
        return MetricsCollector()

    def test_observe_histogram(self, collector):
        """히스토그램 관찰 테스트"""
        values = [10, 20, 30, 40, 50]
        for v in values:
            collector.observe("response_time", v)

        stats = collector.get_histogram_stats("response_time")

        assert stats["count"] == 5
        assert stats["min"] == 10
        assert stats["max"] == 50
        assert stats["avg"] == 30.0

    def test_histogram_percentiles(self, collector):
        """히스토그램 퍼센타일 테스트"""
        # 0-99까지 100개 값
        for i in range(100):
            collector.observe("latency", i)

        stats = collector.get_histogram_stats("latency")

        assert stats["p50"] == 50
        assert stats["p90"] == 90
        assert stats["p99"] == 99

    def test_empty_histogram_stats(self, collector):
        """빈 히스토그램 통계"""
        stats = collector.get_histogram_stats("empty_histogram")

        assert stats["count"] == 0
        assert stats["min"] == 0
        assert stats["max"] == 0
        assert stats["avg"] == 0

    def test_histogram_with_labels(self, collector):
        """레이블을 포함한 히스토그램"""
        collector.observe("request_duration", 100, {"endpoint": "/api/v1"})
        collector.observe("request_duration", 200, {"endpoint": "/api/v1"})
        collector.observe("request_duration", 50, {"endpoint": "/api/v2"})

        stats_v1 = collector.get_histogram_stats("request_duration", {"endpoint": "/api/v1"})
        stats_v2 = collector.get_histogram_stats("request_duration", {"endpoint": "/api/v2"})

        assert stats_v1["count"] == 2
        assert stats_v1["avg"] == 150.0
        assert stats_v2["count"] == 1
        assert stats_v2["avg"] == 50.0


class TestMetricsCollectorTimers:
    """MetricsCollector Timer 메서드 테스트"""

    @pytest.fixture
    def collector(self):
        """MetricsCollector 인스턴스"""
        return MetricsCollector()

    def test_start_stop_timer(self, collector):
        """타이머 시작/정지 테스트"""
        timer_id = collector.start_timer("operation_time")

        time.sleep(0.1)  # 100ms

        elapsed = collector.stop_timer(timer_id)

        assert elapsed is not None
        assert elapsed >= 100  # 최소 100ms
        assert elapsed < 200  # 200ms 미만

    def test_timer_with_labels(self, collector):
        """레이블을 포함한 타이머"""
        timer_id = collector.start_timer(
            "api_call",
            labels={"service": "user-service"}
        )

        time.sleep(0.05)

        elapsed = collector.stop_timer(timer_id)

        assert elapsed is not None
        stats = collector.get_histogram_stats("api_call", {"service": "user-service"})
        assert stats["count"] == 1

    def test_stop_invalid_timer(self, collector):
        """유효하지 않은 타이머 정지"""
        elapsed = collector.stop_timer("invalid-timer-id")
        assert elapsed is None

    def test_timer_context_manager(self, collector):
        """타이머 컨텍스트 매니저 테스트"""
        with collector.timer(collector, "context_timer"):
            time.sleep(0.05)

        stats = collector.get_histogram_stats("context_timer")
        assert stats["count"] == 1
        assert stats["min"] >= 50


class TestMetricsCollectorAgentMethods:
    """Agent 관련 메트릭 메서드 테스트"""

    @pytest.fixture
    def collector(self):
        """MetricsCollector 인스턴스"""
        return MetricsCollector()

    def test_record_agent_execution_success(self, collector):
        """Agent 실행 성공 기록"""
        collector.record_agent_execution(
            agent_id="agent-1",
            agent_name="Test Agent",
            execution_time_ms=150.0,
            success=True,
            task_id="task-1"
        )

        stats = collector.get_agent_stats("agent-1")

        assert stats["total_executions"] == 1
        assert stats["success_count"] == 1
        assert stats["failure_count"] == 0
        assert stats["success_rate"] == 100.0

    def test_record_agent_execution_failure(self, collector):
        """Agent 실행 실패 기록"""
        collector.record_agent_execution(
            agent_id="agent-1",
            agent_name="Test Agent",
            execution_time_ms=50.0,
            success=False
        )

        stats = collector.get_agent_stats("agent-1")

        assert stats["total_executions"] == 1
        assert stats["success_count"] == 0
        assert stats["failure_count"] == 1
        assert stats["success_rate"] == 0.0

    def test_agent_success_rate_calculation(self, collector):
        """Agent 성공률 계산"""
        # 7 성공, 3 실패
        for _ in range(7):
            collector.record_agent_execution(
                agent_id="agent-1",
                agent_name="Test Agent",
                execution_time_ms=100.0,
                success=True
            )

        for _ in range(3):
            collector.record_agent_execution(
                agent_id="agent-1",
                agent_name="Test Agent",
                execution_time_ms=100.0,
                success=False
            )

        stats = collector.get_agent_stats("agent-1")

        assert stats["total_executions"] == 10
        assert stats["success_count"] == 7
        assert stats["failure_count"] == 3
        assert stats["success_rate"] == 70.0

    def test_record_workflow_completion(self, collector):
        """워크플로우 완료 기록"""
        collector.record_workflow_completion(
            task_id="task-1",
            total_time_ms=5000.0,
            steps_count=5,
            success=True
        )

        summary = collector.get_summary()

        assert summary["counters"]["workflow_success_total"] == 1.0

    def test_record_llm_call(self, collector):
        """LLM 호출 기록"""
        collector.record_llm_call(
            model="gpt-4",
            latency_ms=500.0,
            tokens_input=100,
            tokens_output=200,
            success=True
        )

        summary = collector.get_summary()

        # 토큰 합계 확인
        assert "llm_tokens_input_total__model=gpt-4" in summary["counters"]
        assert summary["counters"]["llm_tokens_input_total__model=gpt-4"] == 100.0


class TestMetricsCollectorSummary:
    """메트릭 요약 및 정리 테스트"""

    @pytest.fixture
    def collector(self):
        """MetricsCollector 인스턴스"""
        return MetricsCollector(retention_hours=1)

    def test_get_summary(self, collector):
        """요약 조회 테스트"""
        collector.increment("counter1")
        collector.set_gauge("gauge1", 50.0)
        collector.observe("histogram1", 100.0)

        summary = collector.get_summary()

        assert "total_metrics" in summary
        assert "counters" in summary
        assert "gauges" in summary
        assert "histograms" in summary

    def test_cleanup_old_metrics(self, collector):
        """오래된 메트릭 정리"""
        # 현재 메트릭 추가
        for i in range(10):
            collector.increment("test_metric")

        initial_count = len(collector._metrics)

        # cleanup 실행 (retention 시간 이내이므로 삭제 안됨)
        removed = collector.cleanup_old_metrics()

        # retention 시간 내이므로 0개 삭제
        assert removed == 0
