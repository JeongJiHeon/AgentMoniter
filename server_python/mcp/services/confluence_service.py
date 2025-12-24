from typing import Dict, Any, Optional
from ..base_mcp_service import BaseMCPService
from ..types import (
    MCPServiceConfig,
    MCPOperationRequest,
    MCPOperationResult,
    MCPOperationType,
)


class ConfluencePage:
    def __init__(
        self,
        space_key: str,
        title: str,
        body: Optional[Dict[str, Any]] = None,
        parent_id: Optional[str] = None,
        labels: Optional[list] = None
    ):
        self.space_key = space_key
        self.title = title
        self.body = body
        self.parent_id = parent_id
        self.labels = labels or []


class ConfluenceService(BaseMCPService):
    """
    Confluence MCP 서비스
    
    허용 작업:
    - 페이지 읽기/검색
    - 페이지 초안 생성 (승인 필요)
    - 페이지 업데이트 (승인 필요)
    
    금지 작업:
    - 승인 없는 페이지 공개
    - 승인 없는 권한 변경
    """
    
    def __init__(self, config: MCPServiceConfig):
        super().__init__(config)
        self.base_url = config.baseUrl
        self.api_token = config.credentials.get("apiKey") if config.credentials else None
        self.email = config.credentials.get("email") if config.credentials else None
    
    async def _do_connect(self) -> None:
        if not self.base_url or not self.api_token or not self.email:
            raise ValueError("Confluence base URL, API token, and email are required")
        # TODO: 실제 Confluence API 연결 구현
        print(f"[ConfluenceService] Connected to Confluence at {self.base_url}")
    
    async def _do_disconnect(self) -> None:
        print(f"[ConfluenceService] Disconnected from Confluence")
    
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
            return await self._create_page(payload)
        elif operation == MCPOperationType.UPDATE:
            return await self._update_page(target.id, payload)
        elif operation == MCPOperationType.DELETE:
            return await self._delete_page(target.id)
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
            page = request.payload
            if not page.get("spaceKey"):
                errors.append("Space key is required")
            if not page.get("title"):
                errors.append("Page title is required")
        
        elif operation == MCPOperationType.SEARCH:
            if not request.payload.get("query"):
                errors.append("Search query is required")
        
        return {"errors": errors, "warnings": warnings}
    
    def _should_require_approval(self, request: MCPOperationRequest) -> bool:
        return request.operation in [MCPOperationType.CREATE, MCPOperationType.UPDATE, MCPOperationType.DELETE]
    
    # === Confluence API 작업 구현 ===
    
    async def _read_page(self, page_id: str) -> MCPOperationResult:
        print(f"[ConfluenceService] Reading page: {page_id}")
        return MCPOperationResult(
            success=True,
            data={
                "id": page_id,
                "title": "Sample Page",
                "body": {
                    "storage": {
                        "value": "<p>페이지 내용</p>",
                        "representation": "storage",
                    }
                },
                "version": {"number": 1},
            }
        )
    
    async def _search_pages(self, params: Dict[str, Any]) -> MCPOperationResult:
        print(f"[ConfluenceService] Searching pages: {params.get('query')}")
        return MCPOperationResult(
            success=True,
            data={
                "results": [],
                "totalSize": 0,
            }
        )
    
    async def _list_pages(self, space_key: Optional[str] = None) -> MCPOperationResult:
        print(f"[ConfluenceService] Listing pages in space: {space_key or 'all'}")
        return MCPOperationResult(
            success=True,
            data={"pages": []}
        )
    
    async def _create_page(self, page: Dict[str, Any]) -> MCPOperationResult:
        print(f"[ConfluenceService] Creating page: {page.get('title')} in space {page.get('spaceKey')}")
        return MCPOperationResult(
            success=True,
            data={
                "id": "new-page-id",
                **page,
                "version": {"number": 1},
                "_links": {
                    "webui": f"{self.base_url}/wiki/spaces/{page.get('spaceKey')}/pages/new-page-id"
                }
            },
            metadata={
                "message": "페이지가 생성되었습니다."
            }
        )
    
    async def _update_page(self, page_id: str, updates: Dict[str, Any]) -> MCPOperationResult:
        print(f"[ConfluenceService] Updating page: {page_id}")
        return MCPOperationResult(
            success=True,
            data={
                "id": page_id,
                **updates,
                "version": {"number": 2},
            },
            metadata={
                "message": "페이지가 업데이트되었습니다."
            }
        )
    
    async def _delete_page(self, page_id: str) -> MCPOperationResult:
        print(f"[ConfluenceService] Deleting page: {page_id}")
        return MCPOperationResult(
            success=True,
            data={
                "id": page_id,
                "deleted": True,
            },
            metadata={
                "message": "페이지가 삭제되었습니다."
            }
        )

