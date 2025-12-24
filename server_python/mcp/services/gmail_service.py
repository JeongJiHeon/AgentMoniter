from typing import Dict, Any, List, Optional
from ..base_mcp_service import BaseMCPService
from ..types import (
    MCPServiceConfig,
    MCPOperationRequest,
    MCPOperationResult,
    MCPOperationType,
)


class EmailDraft:
    def __init__(
        self,
        to: List[str],
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        is_html: bool = False,
        attachments: Optional[List[Dict[str, str]]] = None
    ):
        self.to = to
        self.cc = cc or []
        self.bcc = bcc or []
        self.subject = subject
        self.body = body
        self.is_html = is_html
        self.attachments = attachments or []


class GmailService(BaseMCPService):
    """
    Gmail MCP 서비스
    
    허용 작업:
    - 메일 읽기/검색
    - 메일 초안 생성 (승인 필요)
    
    금지 작업:
    - 승인 없는 메일 발송 (send)
    - 승인 없는 자동 답장
    """
    
    def __init__(self, config: MCPServiceConfig):
        super().__init__(config)
    
    async def _do_connect(self) -> None:
        # TODO: 실제 Gmail API OAuth 연결
        print(f"[GmailService] Connected to Gmail")
    
    async def _do_disconnect(self) -> None:
        print(f"[GmailService] Disconnected from Gmail")
    
    async def _do_execute(self, request: MCPOperationRequest) -> MCPOperationResult:
        operation = request.operation
        target = request.target
        payload = request.payload
        
        if operation == MCPOperationType.READ:
            return await self._read_email(target.id)
        elif operation == MCPOperationType.SEARCH:
            return await self._search_emails(payload)
        elif operation == MCPOperationType.LIST:
            return await self._list_emails(payload)
        elif operation == MCPOperationType.CREATE:
            return await self._create_draft(payload)
        elif operation == MCPOperationType.UPDATE:
            return await self._update_draft(target.id, payload)
        elif operation == MCPOperationType.SEND:
            return await self._send_email(target.id, payload)
        elif operation == MCPOperationType.DELETE:
            return await self._delete_email(target.id)
        else:
            return MCPOperationResult(
                success=False,
                error=f"Unsupported operation: {operation}"
            )
    
    async def _do_validate(self, request: MCPOperationRequest) -> Dict[str, list]:
        errors = []
        warnings = []
        
        operation = request.operation
        
        if operation in [MCPOperationType.READ, MCPOperationType.DELETE]:
            if not request.target.id:
                errors.append("Email ID is required")
        
        elif operation in [MCPOperationType.CREATE, MCPOperationType.SEND]:
            draft = request.payload
            if not draft.get("to") or len(draft.get("to", [])) == 0:
                errors.append("At least one recipient is required")
            if not draft.get("subject"):
                warnings.append("Email subject is recommended")
            if not draft.get("body"):
                warnings.append("Email body is empty")
        
        elif operation == MCPOperationType.SEARCH:
            if not request.payload.get("query"):
                errors.append("Search query is required")
        
        # 발송 작업에 대한 추가 경고
        if operation == MCPOperationType.SEND:
            warnings.append("메일이 실제로 발송됩니다. 내용을 다시 확인해주세요.")
        
        return {"errors": errors, "warnings": warnings}
    
    def _should_require_approval(self, request: MCPOperationRequest) -> bool:
        # Gmail에서는 모든 쓰기 작업에 승인 필요
        # 특히 send는 무조건 필수 (APPROVAL_REQUIRED_OPERATIONS에 포함)
        return request.operation in [MCPOperationType.CREATE, MCPOperationType.UPDATE, MCPOperationType.SEND]
    
    # === Gmail API 작업 구현 ===
    
    async def _read_email(self, email_id: str) -> MCPOperationResult:
        print(f"[GmailService] Reading email: {email_id}")
        return MCPOperationResult(
            success=True,
            data={
                "id": email_id,
                "from": "sender@example.com",
                "to": ["recipient@example.com"],
                "subject": "Sample Email",
                "body": "이메일 내용...",
                "date": "2024-01-01T00:00:00Z",
            }
        )
    
    async def _search_emails(self, params: Dict[str, Any]) -> MCPOperationResult:
        print(f"[GmailService] Searching emails: {params.get('query')}")
        return MCPOperationResult(
            success=True,
            data={
                "results": [],
                "hasMore": False,
            }
        )
    
    async def _list_emails(self, params: Dict[str, Any]) -> MCPOperationResult:
        print(f"[GmailService] Listing emails")
        return MCPOperationResult(
            success=True,
            data={
                "emails": [],
                "nextPageToken": None,
            }
        )
    
    async def _create_draft(self, draft: Dict[str, Any]) -> MCPOperationResult:
        print(f"[GmailService] Creating draft to: {', '.join(draft.get('to', []))}")
        return MCPOperationResult(
            success=True,
            data={
                "id": "draft-id",
                **draft,
                "status": "draft",
            },
            metadata={
                "message": "초안이 생성되었습니다. 발송하려면 승인이 필요합니다."
            }
        )
    
    async def _update_draft(self, draft_id: str, updates: Dict[str, Any]) -> MCPOperationResult:
        print(f"[GmailService] Updating draft: {draft_id}")
        return MCPOperationResult(
            success=True,
            data={
                "id": draft_id,
                **updates,
                "status": "draft",
            }
        )
    
    async def _send_email(self, draft_id: Optional[str], email: Dict[str, Any]) -> MCPOperationResult:
        print(f"[GmailService] Sending email to: {', '.join(email.get('to', []))}")
        return MCPOperationResult(
            success=True,
            data={
                "id": draft_id or "sent-email-id",
                **email,
                "status": "sent",
                "sentAt": "2024-01-01T00:00:00Z",
            },
            metadata={
                "message": "이메일이 발송되었습니다."
            }
        )
    
    async def _delete_email(self, email_id: str) -> MCPOperationResult:
        print(f"[GmailService] Deleting email: {email_id}")
        return MCPOperationResult(
            success=True,
            data={
                "id": email_id,
                "deleted": True,
            }
        )

