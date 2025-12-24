from typing import Dict, Any, List, Optional
from ..base_mcp_service import BaseMCPService
from ..types import (
    MCPServiceConfig,
    MCPOperationRequest,
    MCPOperationResult,
    MCPOperationType,
)


class SlackMessage:
    def __init__(
        self,
        channel: str,
        text: Optional[str] = None,
        blocks: Optional[List[Dict[str, Any]]] = None,
        thread_ts: Optional[str] = None,
        reply_broadcast: bool = False
    ):
        self.channel = channel
        self.text = text
        self.blocks = blocks
        self.thread_ts = thread_ts
        self.reply_broadcast = reply_broadcast


class SlackService(BaseMCPService):
    """
    Slack MCP 서비스
    
    허용 작업:
    - 메시지 읽기/검색
    - 채널 목록 조회
    - 메시지 초안 생성 (승인 필요)
    
    금지 작업:
    - 승인 없는 메시지 발송
    - 승인 없는 채널 생성/삭제
    """
    
    def __init__(self, config: MCPServiceConfig):
        super().__init__(config)
        self.bot_token = config.credentials.get("accessToken") if config.credentials else None
        self.webhook_url = config.credentials.get("webhookUrl") if config.credentials else None
    
    async def _do_connect(self) -> None:
        if not self.bot_token:
            raise ValueError("Slack Bot Token is required")
        # TODO: 실제 Slack API 연결 구현
        print(f"[SlackService] Connected to Slack")
    
    async def _do_disconnect(self) -> None:
        print(f"[SlackService] Disconnected from Slack")
    
    async def _do_execute(self, request: MCPOperationRequest) -> MCPOperationResult:
        operation = request.operation
        target = request.target
        payload = request.payload
        
        if operation == MCPOperationType.READ:
            return await self._read_message(target.id)
        elif operation == MCPOperationType.SEARCH:
            return await self._search_messages(payload)
        elif operation == MCPOperationType.LIST:
            if target.type == "channel":
                return await self._list_channels()
            else:
                return await self._list_messages(target.id)
        elif operation == MCPOperationType.CREATE:
            return await self._create_message_draft(payload)
        elif operation == MCPOperationType.SEND:
            return await self._send_message(payload)
        else:
            return MCPOperationResult(
                success=False,
                error=f"Unsupported operation: {operation}"
            )
    
    async def _do_validate(self, request: MCPOperationRequest) -> Dict[str, list]:
        errors = []
        warnings = []
        
        operation = request.operation
        
        if operation in [MCPOperationType.CREATE, MCPOperationType.SEND]:
            message = request.payload
            if not message.get("channel"):
                errors.append("Channel is required")
            if not message.get("text") and not message.get("blocks"):
                errors.append("Message text or blocks required")
        
        elif operation == MCPOperationType.SEARCH:
            if not request.payload.get("query"):
                errors.append("Search query is required")
        
        if operation == MCPOperationType.SEND:
            warnings.append("메시지가 실제로 발송됩니다. 내용을 확인해주세요.")
        
        return {"errors": errors, "warnings": warnings}
    
    def _should_require_approval(self, request: MCPOperationRequest) -> bool:
        return request.operation in [MCPOperationType.CREATE, MCPOperationType.SEND]
    
    # === Slack API 작업 구현 ===
    
    async def _read_message(self, message_ts: str) -> MCPOperationResult:
        print(f"[SlackService] Reading message: {message_ts}")
        return MCPOperationResult(
            success=True,
            data={
                "ts": message_ts,
                "text": "Sample message",
                "user": "U12345",
                "channel": "C12345",
            }
        )
    
    async def _search_messages(self, params: Dict[str, Any]) -> MCPOperationResult:
        print(f"[SlackService] Searching messages: {params.get('query')}")
        return MCPOperationResult(
            success=True,
            data={
                "messages": [],
                "total": 0,
            }
        )
    
    async def _list_channels(self) -> MCPOperationResult:
        print(f"[SlackService] Listing channels")
        return MCPOperationResult(
            success=True,
            data={"channels": []}
        )
    
    async def _list_messages(self, channel_id: str) -> MCPOperationResult:
        print(f"[SlackService] Listing messages in channel: {channel_id}")
        return MCPOperationResult(
            success=True,
            data={
                "messages": [],
                "hasMore": False,
            }
        )
    
    async def _create_message_draft(self, message: Dict[str, Any]) -> MCPOperationResult:
        print(f"[SlackService] Creating message draft for channel: {message.get('channel')}")
        return MCPOperationResult(
            success=True,
            data={
                **message,
                "status": "draft",
            },
            metadata={
                "message": "메시지 초안이 생성되었습니다. 발송하려면 승인이 필요합니다."
            }
        )
    
    async def _send_message(self, message: Dict[str, Any]) -> MCPOperationResult:
        print(f"[SlackService] Sending message to channel: {message.get('channel')}")
        return MCPOperationResult(
            success=True,
            data={
                **message,
                "ts": "1234567890.123456",
                "status": "sent",
            },
            metadata={
                "message": "메시지가 발송되었습니다."
            }
        )

