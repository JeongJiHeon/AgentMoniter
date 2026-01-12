"""
Slack MCP Agent - Slack 연동 백그라운드 Agent

Slack API를 통해 메시지 읽기/쓰기/검색을 수행하는 Worker Agent입니다.
사용자와 직접 소통하지 않고 오케스트레이션에 의해 호출됩니다.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import json

from .base_agent import BaseAgent
from .types import AgentConfig, AgentInput, AgentOutput
from .agent_result import AgentResult, AgentLifecycleStatus, completed, failed, running
from mcp.services.slack_service import SlackService
from mcp.types import (
    MCPServiceConfig,
    MCPServiceType,
    MCPOperationRequest,
    MCPOperationType,
    MCPOperationTarget,
)


class SlackMCPAgent(BaseAgent):
    """
    Slack MCP Agent

    백그라운드에서 Slack 작업을 수행하는 Worker Agent입니다.

    지원 작업:
    - 메시지 읽기 (read_message)
    - 메시지 검색 (search_messages)
    - 채널 목록 조회 (list_channels)
    - 채널 메시지 목록 (list_messages)
    - 메시지 초안 생성 (create_draft) - 승인 필요
    - 메시지 발송 (send_message) - 승인 필요
    """

    AGENT_TYPE = "slack-mcp"
    AGENT_NAME = "Slack MCP Agent"

    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(
                name=self.AGENT_NAME,
                type=self.AGENT_TYPE,
                description="Slack 연동 백그라운드 Agent - 메시지 읽기/쓰기/검색",
                capabilities=["slack", "message", "channel", "search"],
                permissions={
                    "canCreateTickets": True,
                    "canExecuteApproved": True,
                    "canAccessMcp": ["slack"]
                }
            )
        super().__init__(config)

        self._slack_service: Optional[SlackService] = None
        self._bot_token: Optional[str] = None
        self._webhook_url: Optional[str] = None

    def configure(
        self,
        bot_token: str = None,
        webhook_url: str = None
    ) -> None:
        """
        Slack 설정

        Args:
            bot_token: Slack Bot OAuth Token
            webhook_url: Slack Webhook URL (간단한 메시지 발송용)
        """
        self._bot_token = bot_token
        self._webhook_url = webhook_url

        credentials = {}
        if bot_token:
            credentials["accessToken"] = bot_token
        if webhook_url:
            credentials["webhookUrl"] = webhook_url

        self._slack_service = SlackService(MCPServiceConfig(
            type=MCPServiceType.SLACK,
            name="Slack Service",
            enabled=True,
            credentials=credentials
        ))

    async def connect(self) -> bool:
        """Slack 서비스 연결"""
        if not self._slack_service:
            self._log("error", "Slack not configured. Call configure() first.")
            return False

        try:
            await self._slack_service.connect()
            self._log("info", "Connected to Slack API")
            return True
        except Exception as e:
            self._log("error", f"Failed to connect to Slack: {str(e)}")
            return False

    async def disconnect(self) -> None:
        """Slack 서비스 연결 해제"""
        if self._slack_service and self._slack_service.is_connected():
            await self._slack_service.disconnect()
            self._log("info", "Disconnected from Slack API")

    # =========================================================================
    # BaseAgent 추상 메서드 구현
    # =========================================================================

    async def explore(self, input: AgentInput) -> Dict[str, Any]:
        """
        탐색 단계 - 입력 분석 및 작업 유형 결정
        """
        self._log("info", f"Exploring Slack task: {input.content[:100]}...")

        # 입력에서 작업 유형 추출
        operation = self._determine_operation(input)

        return {
            "should_proceed": True,
            "data": {
                "operation": operation,
                "input": input,
                "metadata": input.metadata
            }
        }

    async def structure(self, data: Any) -> Any:
        """
        구조화 단계 - 작업 요청 생성
        """
        self._log("info", "Structuring Slack operation request...")

        operation = data.get("operation", "search")
        input_data = data.get("input")
        metadata = data.get("metadata", {})

        # MCP 작업 요청 생성
        request = self._build_operation_request(operation, input_data, metadata)

        return {
            "operation": operation,
            "request": request,
            "metadata": metadata
        }

    async def validate(self, data: Any) -> Dict[str, Any]:
        """
        검증 단계 - 작업 요청 검증
        """
        self._log("info", "Validating Slack operation request...")

        request = data.get("request")
        if not request:
            return {"is_valid": False, "error": "No operation request"}

        if not self._slack_service:
            return {"is_valid": False, "error": "Slack service not configured"}

        # MCP 서비스 검증
        validation = await self._slack_service.validate(request)

        return {
            "is_valid": validation.isValid,
            "data": data,
            "errors": validation.errors,
            "warnings": validation.warnings,
            "requires_approval": validation.requiresApproval
        }

    async def summarize(self, data: Any) -> AgentOutput:
        """
        요약 단계 - 작업 실행 및 결과 반환
        """
        self._log("info", "Executing Slack operation...")

        request = data.get("request")

        try:
            result = await self._slack_service.execute(request)

            if result.success:
                return AgentOutput(
                    type="slack_result",
                    result={
                        "success": True,
                        "data": result.data,
                        "message": f"Slack 작업 완료: {request.operation.value}"
                    },
                    metadata={
                        "agent_id": self.id,
                        "agent_name": self.name,
                        "operation": request.operation.value
                    }
                )
            else:
                return AgentOutput(
                    type="slack_error",
                    result={
                        "success": False,
                        "error": result.error
                    },
                    metadata={
                        "agent_id": self.id,
                        "agent_name": self.name
                    }
                )
        except Exception as e:
            return AgentOutput(
                type="slack_error",
                result={
                    "success": False,
                    "error": str(e)
                },
                metadata={
                    "agent_id": self.id,
                    "agent_name": self.name
                }
            )

    # =========================================================================
    # Worker Agent 인터페이스 (Orchestration에서 호출)
    # =========================================================================

    async def execute_task(
        self,
        task_description: str,
        context: Dict[str, Any] = None
    ) -> AgentResult:
        """
        오케스트레이션에서 호출하는 작업 실행 메서드

        Args:
            task_description: 작업 설명
            context: 이전 Agent 결과 등 컨텍스트

        Returns:
            AgentResult: 작업 결과
        """
        context = context or {}

        self._log("info", f"Executing Slack task: {task_description}")

        # 서비스 연결 확인
        if not self._slack_service:
            return failed("Slack 서비스가 설정되지 않았습니다. Bot Token을 확인해주세요.")

        if not self._slack_service.is_connected():
            connected = await self.connect()
            if not connected:
                return failed("Slack 서비스에 연결할 수 없습니다.")

        try:
            # 작업 유형 결정
            operation = self._parse_operation_from_description(task_description, context)

            # 작업 실행
            result = await self._execute_operation(operation, task_description, context)

            return result

        except Exception as e:
            self._log("error", f"Slack task failed: {str(e)}")
            return failed(f"Slack 작업 실패: {str(e)}")

    # =========================================================================
    # Slack 작업 메서드
    # =========================================================================

    async def read_message(self, channel: str, message_ts: str) -> AgentResult:
        """메시지 읽기"""
        if not self._ensure_connected():
            return failed("Slack 서비스에 연결되지 않았습니다.")

        request = MCPOperationRequest(
            agentId=self.id,
            service=MCPServiceType.SLACK,
            operation=MCPOperationType.READ,
            target=MCPOperationTarget(type="message", id=message_ts),
            payload={"channel": channel}
        )

        result = await self._slack_service.execute(request)

        if result.success:
            return completed(
                final_data=result.data,
                message=f"메시지를 읽었습니다."
            )
        else:
            return failed(f"메시지 읽기 실패: {result.error}")

    async def search_messages(
        self,
        query: str,
        channel: str = None,
        limit: int = 20
    ) -> AgentResult:
        """메시지 검색"""
        if not self._ensure_connected():
            return failed("Slack 서비스에 연결되지 않았습니다.")

        payload = {"query": query, "limit": limit}
        if channel:
            payload["channel"] = channel

        request = MCPOperationRequest(
            agentId=self.id,
            service=MCPServiceType.SLACK,
            operation=MCPOperationType.SEARCH,
            target=MCPOperationTarget(type="message"),
            payload=payload
        )

        result = await self._slack_service.execute(request)

        if result.success:
            messages = result.data.get("messages", [])
            return completed(
                final_data=result.data,
                message=f"{len(messages)}개의 메시지를 찾았습니다."
            )
        else:
            return failed(f"검색 실패: {result.error}")

    async def list_channels(self) -> AgentResult:
        """채널 목록 조회"""
        if not self._ensure_connected():
            return failed("Slack 서비스에 연결되지 않았습니다.")

        request = MCPOperationRequest(
            agentId=self.id,
            service=MCPServiceType.SLACK,
            operation=MCPOperationType.LIST,
            target=MCPOperationTarget(type="channel")
        )

        result = await self._slack_service.execute(request)

        if result.success:
            channels = result.data.get("channels", [])
            return completed(
                final_data=result.data,
                message=f"{len(channels)}개의 채널이 있습니다."
            )
        else:
            return failed(f"채널 목록 조회 실패: {result.error}")

    async def list_messages(
        self,
        channel: str,
        limit: int = 50
    ) -> AgentResult:
        """채널 메시지 목록 조회"""
        if not self._ensure_connected():
            return failed("Slack 서비스에 연결되지 않았습니다.")

        request = MCPOperationRequest(
            agentId=self.id,
            service=MCPServiceType.SLACK,
            operation=MCPOperationType.LIST,
            target=MCPOperationTarget(type="message", id=channel),
            payload={"limit": limit}
        )

        result = await self._slack_service.execute(request)

        if result.success:
            messages = result.data.get("messages", [])
            return completed(
                final_data=result.data,
                message=f"{len(messages)}개의 메시지가 있습니다."
            )
        else:
            return failed(f"메시지 목록 조회 실패: {result.error}")

    async def create_draft(
        self,
        channel: str,
        text: str,
        blocks: List[Dict[str, Any]] = None,
        thread_ts: str = None
    ) -> AgentResult:
        """
        메시지 초안 생성 (승인 필요)
        """
        if not self._ensure_connected():
            return failed("Slack 서비스에 연결되지 않았습니다.")

        payload = {
            "channel": channel,
            "text": text
        }
        if blocks:
            payload["blocks"] = blocks
        if thread_ts:
            payload["thread_ts"] = thread_ts

        request = MCPOperationRequest(
            agentId=self.id,
            service=MCPServiceType.SLACK,
            operation=MCPOperationType.CREATE,
            target=MCPOperationTarget(type="message"),
            payload=payload,
            requiresApproval=True
        )

        # 검증
        validation = await self._slack_service.validate(request)
        if not validation.isValid:
            return failed(f"검증 실패: {', '.join(validation.errors)}")

        # 승인 필요 시 대기
        if validation.requiresApproval:
            return running(
                message=f"메시지 초안 생성됨 - 승인 대기 중",
                partial_data={
                    "draft": payload,
                    "approval_reason": validation.approvalReason,
                    "channel": channel
                }
            )

        # 실행 (초안 생성)
        result = await self._slack_service.execute(request)

        if result.success:
            return completed(
                final_data=result.data,
                message=f"메시지 초안이 생성되었습니다."
            )
        else:
            return failed(f"초안 생성 실패: {result.error}")

    async def send_message(
        self,
        channel: str,
        text: str,
        blocks: List[Dict[str, Any]] = None,
        thread_ts: str = None,
        reply_broadcast: bool = False
    ) -> AgentResult:
        """
        메시지 발송 (승인 필요)
        """
        if not self._ensure_connected():
            return failed("Slack 서비스에 연결되지 않았습니다.")

        payload = {
            "channel": channel,
            "text": text,
            "reply_broadcast": reply_broadcast
        }
        if blocks:
            payload["blocks"] = blocks
        if thread_ts:
            payload["thread_ts"] = thread_ts

        request = MCPOperationRequest(
            agentId=self.id,
            service=MCPServiceType.SLACK,
            operation=MCPOperationType.SEND,
            target=MCPOperationTarget(type="message"),
            payload=payload,
            requiresApproval=True
        )

        # 검증
        validation = await self._slack_service.validate(request)
        if not validation.isValid:
            return failed(f"검증 실패: {', '.join(validation.errors)}")

        # 승인 필요 시 대기
        if validation.requiresApproval:
            return running(
                message=f"메시지 발송 승인 대기 중",
                partial_data={
                    "message": payload,
                    "approval_reason": validation.approvalReason,
                    "channel": channel
                }
            )

        # 실행
        result = await self._slack_service.execute(request)

        if result.success:
            return completed(
                final_data=result.data,
                message=f"메시지가 발송되었습니다."
            )
        else:
            return failed(f"메시지 발송 실패: {result.error}")

    async def post_notification(
        self,
        channel: str,
        title: str,
        message: str,
        color: str = "good",
        fields: List[Dict[str, str]] = None
    ) -> AgentResult:
        """
        알림 메시지 발송 (Rich format)

        Args:
            channel: 채널 ID 또는 이름
            title: 알림 제목
            message: 알림 내용
            color: 사이드바 색상 (good, warning, danger, 또는 hex)
            fields: 추가 필드 [{title, value, short}]
        """
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": title
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message
                }
            }
        ]

        # 필드 추가
        if fields:
            field_block = {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*{f['title']}*\n{f['value']}"
                    }
                    for f in fields
                ]
            }
            blocks.append(field_block)

        return await self.send_message(
            channel=channel,
            text=f"{title}: {message}",
            blocks=blocks
        )

    # =========================================================================
    # 헬퍼 메서드
    # =========================================================================

    def _ensure_connected(self) -> bool:
        """서비스 연결 상태 확인"""
        return self._slack_service and self._slack_service.is_connected()

    def _determine_operation(self, input: AgentInput) -> str:
        """입력에서 작업 유형 결정"""
        content = input.content.lower()
        metadata = input.metadata or {}

        # 메타데이터에서 명시적 작업 유형
        if "operation" in metadata:
            return metadata["operation"]

        # 내용에서 추론
        if any(word in content for word in ["보내", "발송", "send", "post", "알림"]):
            return "send"
        elif any(word in content for word in ["초안", "작성", "create", "draft"]):
            return "create"
        elif any(word in content for word in ["읽", "조회", "read", "get"]):
            return "read"
        elif any(word in content for word in ["검색", "찾", "search", "find"]):
            return "search"
        elif any(word in content for word in ["채널", "channel", "목록"]):
            return "list_channels"
        elif any(word in content for word in ["메시지 목록", "messages", "history"]):
            return "list_messages"

        return "search"  # 기본값

    def _build_operation_request(
        self,
        operation: str,
        input_data: AgentInput,
        metadata: Dict[str, Any]
    ) -> MCPOperationRequest:
        """MCP 작업 요청 생성"""
        op_type_map = {
            "read": MCPOperationType.READ,
            "search": MCPOperationType.SEARCH,
            "list_channels": MCPOperationType.LIST,
            "list_messages": MCPOperationType.LIST,
            "create": MCPOperationType.CREATE,
            "send": MCPOperationType.SEND,
        }
        op_type = op_type_map.get(operation, MCPOperationType.SEARCH)

        target_type = "channel" if operation == "list_channels" else "message"

        return MCPOperationRequest(
            agentId=self.id,
            service=MCPServiceType.SLACK,
            operation=op_type,
            target=MCPOperationTarget(
                type=target_type,
                id=metadata.get("channel") or metadata.get("message_ts")
            ),
            payload=metadata.get("payload", {"query": input_data.content}),
            requiresApproval=op_type in [MCPOperationType.CREATE, MCPOperationType.SEND]
        )

    def _parse_operation_from_description(
        self,
        description: str,
        context: Dict[str, Any]
    ) -> str:
        """작업 설명에서 작업 유형 파싱"""
        description_lower = description.lower()

        if any(word in description_lower for word in ["보내", "발송", "send", "post", "알림", "notify"]):
            return "send"
        elif any(word in description_lower for word in ["초안", "작성", "create", "draft"]):
            return "create"
        elif any(word in description_lower for word in ["읽", "read", "get", "가져"]):
            return "read"
        elif any(word in description_lower for word in ["검색", "찾", "search", "find"]):
            return "search"
        elif any(word in description_lower for word in ["채널 목록", "list channels"]):
            return "list_channels"
        elif any(word in description_lower for word in ["메시지 목록", "history", "messages"]):
            return "list_messages"

        return context.get("default_operation", "search")

    async def _execute_operation(
        self,
        operation: str,
        description: str,
        context: Dict[str, Any]
    ) -> AgentResult:
        """작업 실행"""
        if operation == "read":
            channel = context.get("channel")
            message_ts = context.get("message_ts")
            if not channel or not message_ts:
                return failed("채널과 메시지 타임스탬프가 필요합니다.")
            return await self.read_message(channel, message_ts)

        elif operation == "search":
            query = context.get("query", description)
            channel = context.get("channel")
            limit = context.get("limit", 20)
            return await self.search_messages(query, channel, limit)

        elif operation == "list_channels":
            return await self.list_channels()

        elif operation == "list_messages":
            channel = context.get("channel")
            if not channel:
                return failed("채널이 필요합니다.")
            limit = context.get("limit", 50)
            return await self.list_messages(channel, limit)

        elif operation == "create":
            channel = context.get("channel")
            if not channel:
                return failed("채널이 필요합니다.")
            text = context.get("text", description)
            blocks = context.get("blocks")
            thread_ts = context.get("thread_ts")
            return await self.create_draft(channel, text, blocks, thread_ts)

        elif operation == "send":
            channel = context.get("channel")
            if not channel:
                return failed("채널이 필요합니다.")
            text = context.get("text", description)
            blocks = context.get("blocks")
            thread_ts = context.get("thread_ts")
            reply_broadcast = context.get("reply_broadcast", False)
            return await self.send_message(channel, text, blocks, thread_ts, reply_broadcast)

        elif operation == "notify":
            channel = context.get("channel")
            if not channel:
                return failed("채널이 필요합니다.")
            title = context.get("title", "알림")
            message = context.get("message", description)
            color = context.get("color", "good")
            fields = context.get("fields")
            return await self.post_notification(channel, title, message, color, fields)

        else:
            return failed(f"지원하지 않는 작업: {operation}")

    def _log(self, level: str, message: str):
        """로그 출력"""
        print(f"[{self.name}] [{level.upper()}] {message}")


# 싱글톤 인스턴스 (필요 시 사용)
slack_mcp_agent = SlackMCPAgent()
