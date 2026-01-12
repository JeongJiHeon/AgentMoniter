"""
Handler Unit Tests

handlers/ 모듈의 단위 테스트입니다.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

# 테스트 대상 모듈 import (상대 경로 조정 필요)
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from handlers.approval_handlers import ApprovalHandlers
from handlers.config_handlers import ConfigHandlers


class TestApprovalHandlers:
    """ApprovalHandlers 테스트"""

    @pytest.fixture
    def approval_handler(self, mock_ws_server, mock_agent_registry):
        """ApprovalHandlers 인스턴스 생성"""
        return ApprovalHandlers(
            ws_server=mock_ws_server,
            agent_registry=mock_agent_registry
        )

    @pytest.mark.asyncio
    async def test_handle_approve_request_agent_not_found(
        self,
        approval_handler,
        sample_approval_payload
    ):
        """Agent가 없을 때 승인 요청 처리"""
        # Agent가 없는 경우
        approval_handler.agent_registry.get_agent.return_value = None

        await approval_handler.handle_approve_request(
            "client-1",
            sample_approval_payload
        )

        # Agent를 조회했는지 확인
        approval_handler.agent_registry.get_agent.assert_called_once_with(
            sample_approval_payload["agentId"]
        )

    @pytest.mark.asyncio
    async def test_handle_approve_request_success(
        self,
        approval_handler,
        sample_approval_payload,
        mock_agent
    ):
        """정상적인 승인 요청 처리"""
        # Agent가 있는 경우
        approval_handler.agent_registry.get_agent.return_value = mock_agent

        await approval_handler.handle_approve_request(
            "client-1",
            sample_approval_payload
        )

        # Agent 상태 업데이트 확인
        approval_handler.ws_server.broadcast_agent_update.assert_called()
        approval_handler.ws_server.broadcast_notification.assert_called()

    @pytest.mark.asyncio
    async def test_handle_reject_request_success(
        self,
        approval_handler,
        sample_approval_payload,
        mock_agent
    ):
        """정상적인 거부 요청 처리"""
        approval_handler.agent_registry.get_agent.return_value = mock_agent

        await approval_handler.handle_reject_request(
            "client-1",
            sample_approval_payload
        )

        # 알림 브로드캐스트 확인
        approval_handler.ws_server.broadcast_notification.assert_called_with(
            f"Ticket {sample_approval_payload['ticketId']} rejected.",
            "info"
        )


class TestConfigHandlers:
    """ConfigHandlers 테스트"""

    @pytest.fixture
    def config_handler(self, mock_ws_server, mock_agent_registry):
        """ConfigHandlers 인스턴스 생성"""
        return ConfigHandlers(
            ws_server=mock_ws_server,
            agent_registry=mock_agent_registry
        )

    def test_config_handler_initialization(self, config_handler):
        """ConfigHandler 초기화 테스트"""
        assert config_handler is not None
        assert config_handler.ws_server is not None
        assert config_handler.agent_registry is not None
