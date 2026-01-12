#!/usr/bin/env python3
"""
Orchestration Logger - 구조화된 로깅

Agent 활동 및 워크플로우 상태를 구조화된 형태로 로깅합니다.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum


class LogLevel(str, Enum):
    """로그 레벨"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    DECISION = "decision"  # Agent 의사결정


@dataclass
class LogEntry:
    """구조화된 로그 엔트리"""
    timestamp: str
    level: LogLevel
    agent_id: str
    agent_name: str
    message: str
    task_id: Optional[str] = None
    details: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "timestamp": self.timestamp,
            "level": self.level.value,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "message": self.message,
            "task_id": self.task_id,
            "details": self.details,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        """JSON 문자열로 변환"""
        return json.dumps(self.to_dict(), ensure_ascii=False)


class OrchestrationLogger:
    """
    오케스트레이션 로거

    책임:
    - 구조화된 로그 생성
    - WebSocket 브로드캐스트
    - 로그 저장 (선택적)
    """

    def __init__(
        self,
        ws_broadcast_callback: Optional[Callable] = None,
        enable_console: bool = True,
        enable_file: bool = False,
        log_file_path: Optional[str] = None
    ):
        """
        Args:
            ws_broadcast_callback: WebSocket 브로드캐스트 콜백
            enable_console: 콘솔 출력 활성화
            enable_file: 파일 로깅 활성화
            log_file_path: 로그 파일 경로
        """
        self._ws_callback = ws_broadcast_callback
        self._enable_console = enable_console
        self._enable_file = enable_file
        self._log_file_path = log_file_path

        # Python 로거 설정
        self._logger = logging.getLogger("orchestration")
        self._logger.setLevel(logging.DEBUG)

        if enable_console and not self._logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter('[%(name)s] %(message)s')
            )
            self._logger.addHandler(handler)

        if enable_file and log_file_path:
            file_handler = logging.FileHandler(log_file_path)
            file_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(message)s')
            )
            self._logger.addHandler(file_handler)

    def set_ws_callback(self, callback: Callable) -> None:
        """WebSocket 브로드캐스트 콜백 설정"""
        self._ws_callback = callback

    def log(
        self,
        agent_id: str,
        agent_name: str,
        level: LogLevel,
        message: str,
        task_id: Optional[str] = None,
        details: Optional[str] = None,
        **metadata
    ) -> LogEntry:
        """
        로그 기록

        Args:
            agent_id: Agent ID
            agent_name: Agent 이름
            level: 로그 레벨
            message: 로그 메시지
            task_id: Task ID
            details: 상세 정보
            **metadata: 추가 메타데이터

        Returns:
            생성된 LogEntry
        """
        entry = LogEntry(
            timestamp=datetime.now().isoformat(),
            level=level,
            agent_id=agent_id,
            agent_name=agent_name,
            message=message,
            task_id=task_id,
            details=details,
            metadata=metadata
        )

        # 콘솔 출력
        if self._enable_console:
            self._console_output(entry)

        # WebSocket 브로드캐스트
        if self._ws_callback:
            self._ws_callback(
                agent_id=agent_id,
                agent_name=agent_name,
                log_type=level.value,
                message=message,
                details=details or "",
                task_id=task_id
            )

        return entry

    def _console_output(self, entry: LogEntry) -> None:
        """콘솔 출력"""
        level_icons = {
            LogLevel.DEBUG: "🔍",
            LogLevel.INFO: "ℹ️",
            LogLevel.WARNING: "⚠️",
            LogLevel.ERROR: "❌",
            LogLevel.DECISION: "🎯",
        }
        icon = level_icons.get(entry.level, "")
        print(f"[{entry.agent_name}] {icon} {entry.message}")

    # Convenience methods
    def info(
        self,
        agent_id: str,
        agent_name: str,
        message: str,
        task_id: Optional[str] = None,
        details: Optional[str] = None,
        **metadata
    ) -> LogEntry:
        """INFO 레벨 로그"""
        return self.log(
            agent_id, agent_name, LogLevel.INFO,
            message, task_id, details, **metadata
        )

    def warning(
        self,
        agent_id: str,
        agent_name: str,
        message: str,
        task_id: Optional[str] = None,
        details: Optional[str] = None,
        **metadata
    ) -> LogEntry:
        """WARNING 레벨 로그"""
        return self.log(
            agent_id, agent_name, LogLevel.WARNING,
            message, task_id, details, **metadata
        )

    def error(
        self,
        agent_id: str,
        agent_name: str,
        message: str,
        task_id: Optional[str] = None,
        details: Optional[str] = None,
        **metadata
    ) -> LogEntry:
        """ERROR 레벨 로그"""
        return self.log(
            agent_id, agent_name, LogLevel.ERROR,
            message, task_id, details, **metadata
        )

    def decision(
        self,
        agent_id: str,
        agent_name: str,
        message: str,
        task_id: Optional[str] = None,
        details: Optional[str] = None,
        **metadata
    ) -> LogEntry:
        """DECISION 레벨 로그 (Agent 의사결정)"""
        return self.log(
            agent_id, agent_name, LogLevel.DECISION,
            message, task_id, details, **metadata
        )


# 전역 로거 인스턴스
orchestration_logger = OrchestrationLogger()
