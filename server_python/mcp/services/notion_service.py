from typing import Dict, Any, Optional
from ..base_mcp_service import BaseMCPService
from ..types import (
    MCPServiceConfig,
    MCPOperationRequest,
    MCPOperationResult,
    MCPOperationType,
)


class NotionService(BaseMCPService):
    """
    Notion MCP 서비스
    
    허용 작업:
    - 페이지 읽기/검색
    - 페이지 초안 생성 (승인 필요)
    - 페이지 업데이트 (승인 필요)
    
    금지 작업:
    - 승인 없는 페이지 공개
    - 승인 없는 공유 설정 변경
    """
    
    def __init__(self, config: MCPServiceConfig):
        super().__init__(config)
        self.api_key = config.credentials.get("apiKey") if config.credentials else None
    
    async def _do_connect(self) -> None:
        if not self.api_key:
            raise ValueError("Notion API key is required")
        # TODO: 실제 Notion API 연결 구현
        print(f"[NotionService] Connected to Notion")
    
    async def _do_disconnect(self) -> None:
        print(f"[NotionService] Disconnected from Notion")
    
    async def _do_execute(self, request: MCPOperationRequest) -> MCPOperationResult:
        operation = request.operation
        target = request.target
        payload = request.payload
        
        if operation == MCPOperationType.READ:
            return await self._read_page(target.id)
        elif operation == MCPOperationType.SEARCH:
            return await self._search_pages(payload)
        elif operation == MCPOperationType.LIST:
            return await self._list_pages(target.path)
        elif operation == MCPOperationType.CREATE:
            return await self._create_page(target.path, payload)
        elif operation == MCPOperationType.UPDATE:
            return await self._update_page(target.id, payload)
        elif operation == MCPOperationType.DELETE:
            return await self._archive_page(target.id)
        else:
            return MCPOperationResult(
                success=False,
                error=f"Unsupported operation: {operation}"
            )
    
    async def _do_validate(self, request: MCPOperationRequest) -> Dict[str, list]:
        errors = []
        warnings = []
        
        operation = request.operation
        
        if operation in [MCPOperationType.READ, MCPOperationType.UPDATE, MCPOperationType.DELETE]:
            if not request.target.id:
                errors.append("Page ID is required")
        
        elif operation == MCPOperationType.CREATE:
            if not request.target.path:
                errors.append("Parent page path is required")
            if not request.payload.get("title"):
                warnings.append("Page title is recommended")
        
        elif operation == MCPOperationType.SEARCH:
            if not request.payload.get("query"):
                errors.append("Search query is required")
        
        return {"errors": errors, "warnings": warnings}
    
    def _should_require_approval(self, request: MCPOperationRequest) -> bool:
        # Notion에서는 create, update도 승인 필요
        return request.operation in [MCPOperationType.CREATE, MCPOperationType.UPDATE]
    
    # === Notion API 작업 구현 ===
    
    async def _read_page(self, page_id: str) -> MCPOperationResult:
        # TODO: 실제 Notion API 호출
        print(f"[NotionService] Reading page: {page_id}")
        return MCPOperationResult(
            success=True,
            data={
                "id": page_id,
                "title": "Sample Page",
                "content": "페이지 내용...",
            }
        )
    
    async def _search_pages(self, params: Dict[str, Any]) -> MCPOperationResult:
        print(f"[NotionService] Searching pages: {params.get('query')}")
        return MCPOperationResult(
            success=True,
            data={
                "results": [],
                "hasMore": False,
            }
        )
    
    async def _list_pages(self, parent_path: Optional[str] = None) -> MCPOperationResult:
        print(f"[NotionService] Listing pages in: {parent_path or 'root'}")
        return MCPOperationResult(
            success=True,
            data={"pages": []}
        )
    
    async def _create_page(self, parent_path: str, payload: Dict[str, Any]) -> MCPOperationResult:
        print(f"[NotionService] Creating page in: {parent_path}")
        return MCPOperationResult(
            success=True,
            data={
                "id": "new-page-id",
                "url": "https://notion.so/new-page",
                **payload,
            }
        )
    
    async def _update_page(self, page_id: str, payload: Dict[str, Any]) -> MCPOperationResult:
        print(f"[NotionService] Updating page: {page_id}")
        return MCPOperationResult(
            success=True,
            data={
                "id": page_id,
                **payload,
            }
        )
    
    async def _archive_page(self, page_id: str) -> MCPOperationResult:
        print(f"[NotionService] Archiving page: {page_id}")
        return MCPOperationResult(
            success=True,
            data={
                "id": page_id,
                "archived": True,
            }
        )

