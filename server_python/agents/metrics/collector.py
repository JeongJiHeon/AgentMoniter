#!/usr/bin/env python3
"""
Metrics Collector - 성능 메트릭 수집

Agent 및 워크플로우 성능 메트릭을 수집하고 분석합니다.
"""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum


class MetricType(str, Enum):
    """메트릭 유형"""
    COUNTER = "counter"       # 증가하는 카운터
    GAUGE = "gauge"           # 현재 값
    HISTOGRAM = "histogram"   # 분포
    TIMER = "timer"           # 시간 측정


@dataclass
class MetricEntry:
    """메트릭 엔트리"""
    name: str
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.GAUGE


@dataclass
class TimerContext:
    """타이머 컨텍스트"""
    start_time: float
    name: str
    labels: Dict[str, str]


class MetricsCollector:
    """
    메트릭 수집기

    책임:
    - Agent 실행 시간 추적
    - 성공/실패 카운트
    - 워크플로우 완료 시간
    - 리소스 사용량
    """

    def __init__(self, retention_hours: int = 24):
        """
        Args:
            retention_hours: 메트릭 보관 시간
        """
        self._retention_hours = retention_hours
        self._metrics: List[MetricEntry] = []
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._active_timers: Dict[str, TimerContext] = {}

    # =========================================================================
    # Counter Methods
    # =========================================================================

    def increment(
        self,
        name: str,
        value: float = 1.0,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """카운터 증가"""
        key = self._make_key(name, labels)
        self._counters[key] += value

        self._metrics.append(MetricEntry(
            name=name,
            value=self._counters[key],
            timestamp=datetime.now(),
            labels=labels or {},
            metric_type=MetricType.COUNTER
        ))

    def get_counter(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None
    ) -> float:
        """카운터 값 조회"""
        key = self._make_key(name, labels)
        return self._counters.get(key, 0.0)

    # =========================================================================
    # Gauge Methods
    # =========================================================================

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """게이지 설정"""
        key = self._make_key(name, labels)
        self._gauges[key] = value

        self._metrics.append(MetricEntry(
            name=name,
            value=value,
            timestamp=datetime.now(),
            labels=labels or {},
            metric_type=MetricType.GAUGE
        ))

    def get_gauge(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None
    ) -> Optional[float]:
        """게이지 값 조회"""
        key = self._make_key(name, labels)
        return self._gauges.get(key)

    # =========================================================================
    # Histogram Methods
    # =========================================================================

    def observe(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """히스토그램에 값 추가"""
        key = self._make_key(name, labels)
        self._histograms[key].append(value)

        self._metrics.append(MetricEntry(
            name=name,
            value=value,
            timestamp=datetime.now(),
            labels=labels or {},
            metric_type=MetricType.HISTOGRAM
        ))

    def get_histogram_stats(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None
    ) -> Dict[str, float]:
        """히스토그램 통계"""
        key = self._make_key(name, labels)
        values = self._histograms.get(key, [])

        if not values:
            return {
                "count": 0,
                "min": 0,
                "max": 0,
                "avg": 0,
                "p50": 0,
                "p90": 0,
                "p99": 0
            }

        sorted_values = sorted(values)
        count = len(values)

        return {
            "count": count,
            "min": sorted_values[0],
            "max": sorted_values[-1],
            "avg": sum(values) / count,
            "p50": self._percentile(sorted_values, 50),
            "p90": self._percentile(sorted_values, 90),
            "p99": self._percentile(sorted_values, 99)
        }

    # =========================================================================
    # Timer Methods
    # =========================================================================

    def start_timer(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None
    ) -> str:
        """타이머 시작"""
        timer_id = f"{name}_{datetime.now().timestamp()}"
        self._active_timers[timer_id] = TimerContext(
            start_time=time.time(),
            name=name,
            labels=labels or {}
        )
        return timer_id

    def stop_timer(self, timer_id: str) -> Optional[float]:
        """타이머 정지 및 기록"""
        if timer_id not in self._active_timers:
            return None

        context = self._active_timers.pop(timer_id)
        elapsed_ms = (time.time() - context.start_time) * 1000

        # 히스토그램에 기록
        self.observe(context.name, elapsed_ms, context.labels)

        return elapsed_ms

    class timer:
        """타이머 컨텍스트 매니저"""

        def __init__(
            self,
            collector: 'MetricsCollector',
            name: str,
            labels: Optional[Dict[str, str]] = None
        ):
            self.collector = collector
            self.name = name
            self.labels = labels
            self.timer_id = None

        def __enter__(self):
            self.timer_id = self.collector.start_timer(self.name, self.labels)
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.collector.stop_timer(self.timer_id)

    # =========================================================================
    # Agent-specific Methods
    # =========================================================================

    def record_agent_execution(
        self,
        agent_id: str,
        agent_name: str,
        execution_time_ms: float,
        success: bool,
        task_id: Optional[str] = None
    ) -> None:
        """Agent 실행 기록"""
        labels = {
            "agent_id": agent_id,
            "agent_name": agent_name,
            "success": str(success).lower()
        }
        if task_id:
            labels["task_id"] = task_id

        # 실행 시간 기록
        self.observe(
            "agent_execution_time_ms",
            execution_time_ms,
            labels
        )

        # 성공/실패 카운트
        if success:
            self.increment("agent_success_total", 1, {"agent_id": agent_id})
        else:
            self.increment("agent_failure_total", 1, {"agent_id": agent_id})

        # 총 실행 횟수
        self.increment("agent_execution_total", 1, {"agent_id": agent_id})

    def record_workflow_completion(
        self,
        task_id: str,
        total_time_ms: float,
        steps_count: int,
        success: bool
    ) -> None:
        """워크플로우 완료 기록"""
        labels = {
            "task_id": task_id,
            "success": str(success).lower()
        }

        # 완료 시간 기록
        self.observe("workflow_completion_time_ms", total_time_ms, labels)

        # 스텝 수 기록
        self.observe("workflow_steps_count", steps_count, labels)

        # 완료 카운트
        if success:
            self.increment("workflow_success_total")
        else:
            self.increment("workflow_failure_total")

    def record_llm_call(
        self,
        model: str,
        latency_ms: float,
        tokens_input: int = 0,
        tokens_output: int = 0,
        success: bool = True
    ) -> None:
        """LLM 호출 기록"""
        labels = {"model": model, "success": str(success).lower()}

        self.observe("llm_latency_ms", latency_ms, labels)
        self.increment("llm_tokens_input_total", tokens_input, {"model": model})
        self.increment("llm_tokens_output_total", tokens_output, {"model": model})
        self.increment("llm_calls_total", 1, labels)

    # =========================================================================
    # Query Methods
    # =========================================================================

    def get_agent_stats(self, agent_id: str) -> Dict[str, Any]:
        """Agent 통계 조회"""
        success_count = self.get_counter(
            "agent_success_total",
            {"agent_id": agent_id}
        )
        failure_count = self.get_counter(
            "agent_failure_total",
            {"agent_id": agent_id}
        )
        total_count = self.get_counter(
            "agent_execution_total",
            {"agent_id": agent_id}
        )

        execution_stats = self.get_histogram_stats(
            "agent_execution_time_ms",
            {"agent_id": agent_id}
        )

        success_rate = (
            success_count / total_count * 100
            if total_count > 0 else 0
        )

        return {
            "agent_id": agent_id,
            "total_executions": int(total_count),
            "success_count": int(success_count),
            "failure_count": int(failure_count),
            "success_rate": round(success_rate, 2),
            "execution_time": execution_stats
        }

    def get_summary(self) -> Dict[str, Any]:
        """전체 메트릭 요약"""
        # 최근 메트릭만 필터링
        cutoff = datetime.now() - timedelta(hours=self._retention_hours)
        recent_metrics = [
            m for m in self._metrics
            if m.timestamp > cutoff
        ]

        return {
            "total_metrics": len(recent_metrics),
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {
                name: self.get_histogram_stats(name)
                for name in set(h.split("__")[0] for h in self._histograms.keys())
            },
            "retention_hours": self._retention_hours
        }

    def cleanup_old_metrics(self) -> int:
        """오래된 메트릭 정리"""
        cutoff = datetime.now() - timedelta(hours=self._retention_hours)
        original_count = len(self._metrics)

        self._metrics = [
            m for m in self._metrics
            if m.timestamp > cutoff
        ]

        # 히스토그램도 정리 (최근 1000개만 유지)
        for key in self._histograms:
            if len(self._histograms[key]) > 1000:
                self._histograms[key] = self._histograms[key][-1000:]

        return original_count - len(self._metrics)

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _make_key(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None
    ) -> str:
        """메트릭 키 생성"""
        if not labels:
            return name

        label_str = "__".join(
            f"{k}={v}" for k, v in sorted(labels.items())
        )
        return f"{name}__{label_str}"

    def _percentile(self, sorted_values: List[float], p: int) -> float:
        """퍼센타일 계산"""
        if not sorted_values:
            return 0

        index = int(len(sorted_values) * p / 100)
        index = min(index, len(sorted_values) - 1)
        return sorted_values[index]


# 전역 메트릭 수집기 인스턴스
metrics_collector = MetricsCollector()
