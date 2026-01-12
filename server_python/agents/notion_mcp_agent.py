"""
Notion MCP Agent - Notion 연동 백그라운드 Agent

Notion API를 통해 페이지 읽기/쓰기/검색을 수행하는 Worker Agent입니다.
사용자와 직접 소통하지 않고 오케스트레이션에 의해 호출됩니다.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import json

from .base_agent import BaseAgent
from .types import AgentConfig, AgentInput, AgentOutput
from .agent_result import AgentResult, AgentLifecycleStatus, completed, failed, running
from mcp.services.notion_service import NotionService
from mcp.types import (
    MCPServiceConfig,
    MCPServiceType,
    MCPOperationRequest,
    MCPOperationType,
    MCPOperationTarget,
)


class NotionMCPAgent(BaseAgent):
    """
    Notion MCP Agent

    백그라운드에서 Notion 작업을 수행하는 Worker Agent입니다.

    지원 작업:
    - 페이지 읽기 (read_page)
    - 페이지 검색 (search_pages)
    - 페이지 목록 조회 (list_pages)
    - 페이지 생성 (create_page) - 승인 필요
    - 페이지 업데이트 (update_page) - 승인 필요
    - 페이지 삭제/보관 (archive_page) - 승인 필요
    """

    AGENT_TYPE = "notion-mcp"
    AGENT_NAME = "Notion MCP Agent"

    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(
                name=self.AGENT_NAME,
                type=self.AGENT_TYPE,
                description="Notion 연동 백그라운드 Agent - 페이지 읽기/쓰기/검색",
                capabilities=["notion", "read", "write", "search"],
                permissions={
                    "canCreateTickets": True,
                    "canExecuteApproved": True,
                    "canAccessMcp": ["notion"]
                }
            )
        super().__init__(config)

        self._notion_service: Optional[NotionService] = None
        self._api_key: Optional[str] = None

    def configure(self, api_key: str) -> None:
        """
        Notion API 키 설정

        Args:
            api_key: Notion Integration API Key
        """
        self._api_key = api_key
        self._notion_service = NotionService(MCPServiceConfig(
            type=MCPServiceType.NOTION,
            name="Notion Service",
            enabled=True,
            credentials={"apiKey": api_key}
        ))

    async def connect(self) -> bool:
        """Notion 서비스 연결"""
        if not self._notion_service:
            self._log("error", "Notion API key not configured. Call configure() first.")
            return False

        try:
            await self._notion_service.connect()
            self._log("info", "Connected to Notion API")
            return True
        except Exception as e:
            self._log("error", f"Failed to connect to Notion: {str(e)}")
            return False

    async def disconnect(self) -> None:
        """Notion 서비스 연결 해제"""
        if self._notion_service and self._notion_service.is_connected():
            await self._notion_service.disconnect()
            self._log("info", "Disconnected from Notion API")

    # =========================================================================
    # BaseAgent 추상 메서드 구현
    # =========================================================================

    async def explore(self, input: AgentInput) -> Dict[str, Any]:
        """
        탐색 단계 - 입력 분석 및 작업 유형 결정
        """
        self._log("info", f"Exploring Notion task: {input.content[:100]}...")

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
        self._log("info", "Structuring Notion operation request...")

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
        self._log("info", "Validating Notion operation request...")

        request = data.get("request")
        if not request:
            return {"is_valid": False, "error": "No operation request"}

        if not self._notion_service:
            return {"is_valid": False, "error": "Notion service not configured"}

        # MCP 서비스 검증
        validation = await self._notion_service.validate(request)

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
        self._log("info", "Executing Notion operation...")

        request = data.get("request")

        try:
            result = await self._notion_service.execute(request)

            if result.success:
                return AgentOutput(
                    type="notion_result",
                    result={
                        "success": True,
                        "data": result.data,
                        "message": f"Notion 작업 완료: {request.operation.value}"
                    },
                    metadata={
                        "agent_id": self.id,
                        "agent_name": self.name,
                        "operation": request.operation.value
                    }
                )
            else:
                return AgentOutput(
                    type="notion_error",
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
                type="notion_error",
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

        self._log("info", f"Executing Notion task: {task_description}")

        # 서비스 연결 확인
        if not self._notion_service:
            return failed("Notion 서비스가 설정되지 않았습니다. API 키를 확인해주세요.")

        if not self._notion_service.is_connected():
            connected = await self.connect()
            if not connected:
                return failed("Notion 서비스에 연결할 수 없습니다.")

        try:
            # 작업 유형 결정
            operation = self._parse_operation_from_description(task_description, context)

            # 작업 실행
            result = await self._execute_operation(operation, task_description, context)

            return result

        except Exception as e:
            self._log("error", f"Notion task failed: {str(e)}")
            return failed(f"Notion 작업 실패: {str(e)}")

    # =========================================================================
    # Notion 작업 메서드
    # =========================================================================

    async def read_page(self, page_id: str) -> AgentResult:
        """페이지 읽기"""
        if not self._ensure_connected():
            return failed("Notion 서비스에 연결되지 않았습니다.")

        request = MCPOperationRequest(
            agentId=self.id,
            service=MCPServiceType.NOTION,
            operation=MCPOperationType.READ,
            target=MCPOperationTarget(type="page", id=page_id)
        )

        result = await self._notion_service.execute(request)

        if result.success:
            return completed(
                final_data=result.data,
                message=f"페이지를 읽었습니다: {result.data.get('title', page_id)}"
            )
        else:
            return failed(f"페이지 읽기 실패: {result.error}")

    async def search_pages(self, query: str, filters: Dict[str, Any] = None) -> AgentResult:
        """페이지 검색"""
        if not self._ensure_connected():
            return failed("Notion 서비스에 연결되지 않았습니다.")

        request = MCPOperationRequest(
            agentId=self.id,
            service=MCPServiceType.NOTION,
            operation=MCPOperationType.SEARCH,
            target=MCPOperationTarget(type="page"),
            payload={"query": query, **(filters or {})}
        )

        result = await self._notion_service.execute(request)

        if result.success:
            results = result.data.get("results", [])
            return completed(
                final_data=result.data,
                message=f"{len(results)}개의 페이지를 찾았습니다."
            )
        else:
            return failed(f"검색 실패: {result.error}")

    async def list_pages(self, parent_path: str = None) -> AgentResult:
        """페이지 목록 조회"""
        if not self._ensure_connected():
            return failed("Notion 서비스에 연결되지 않았습니다.")

        request = MCPOperationRequest(
            agentId=self.id,
            service=MCPServiceType.NOTION,
            operation=MCPOperationType.LIST,
            target=MCPOperationTarget(type="page", path=parent_path)
        )

        result = await self._notion_service.execute(request)

        if result.success:
            pages = result.data.get("pages", [])
            return completed(
                final_data=result.data,
                message=f"{len(pages)}개의 페이지가 있습니다."
            )
        else:
            return failed(f"목록 조회 실패: {result.error}")

    async def create_page(
        self,
        parent_path: str,
        title: str,
        content: str = "",
        properties: Dict[str, Any] = None
    ) -> AgentResult:
        """
        페이지 생성 (승인 필요)
        """
        if not self._ensure_connected():
            return failed("Notion 서비스에 연결되지 않았습니다.")

        request = MCPOperationRequest(
            agentId=self.id,
            service=MCPServiceType.NOTION,
            operation=MCPOperationType.CREATE,
            target=MCPOperationTarget(type="page", path=parent_path),
            payload={
                "title": title,
                "content": content,
                **(properties or {})
            },
            requiresApproval=True
        )

        # 검증
        validation = await self._notion_service.validate(request)
        if not validation.isValid:
            return failed(f"검증 실패: {', '.join(validation.errors)}")

        # 승인 필요 시 대기
        if validation.requiresApproval:
            return running(
                message=f"페이지 생성 승인 대기 중: {title}",
                partial_data={
                    "request": request.model_dump(),
                    "approval_reason": validation.approvalReason
                }
            )

        # 실행
        result = await self._notion_service.execute(request)

        if result.success:
            return completed(
                final_data=result.data,
                message=f"페이지가 생성되었습니다: {title}"
            )
        else:
            return failed(f"페이지 생성 실패: {result.error}")

    async def update_page(
        self,
        page_id: str,
        title: str = None,
        content: str = None,
        properties: Dict[str, Any] = None
    ) -> AgentResult:
        """
        페이지 업데이트 (승인 필요)
        """
        if not self._ensure_connected():
            return failed("Notion 서비스에 연결되지 않았습니다.")

        payload = {}
        if title:
            payload["title"] = title
        if content:
            payload["content"] = content
        if properties:
            payload.update(properties)

        request = MCPOperationRequest(
            agentId=self.id,
            service=MCPServiceType.NOTION,
            operation=MCPOperationType.UPDATE,
            target=MCPOperationTarget(type="page", id=page_id),
            payload=payload,
            requiresApproval=True
        )

        result = await self._notion_service.execute(request)

        if result.success:
            return completed(
                final_data=result.data,
                message=f"페이지가 업데이트되었습니다: {page_id}"
            )
        else:
            return failed(f"페이지 업데이트 실패: {result.error}")

    async def archive_page(self, page_id: str) -> AgentResult:
        """
        페이지 보관 (삭제, 승인 필요)
        """
        if not self._ensure_connected():
            return failed("Notion 서비스에 연결되지 않았습니다.")

        request = MCPOperationRequest(
            agentId=self.id,
            service=MCPServiceType.NOTION,
            operation=MCPOperationType.DELETE,
            target=MCPOperationTarget(type="page", id=page_id),
            requiresApproval=True
        )

        result = await self._notion_service.execute(request)

        if result.success:
            return completed(
                final_data=result.data,
                message=f"페이지가 보관되었습니다: {page_id}"
            )
        else:
            return failed(f"페이지 보관 실패: {result.error}")

    # =========================================================================
    # 헬퍼 메서드
    # =========================================================================

    def _ensure_connected(self) -> bool:
        """서비스 연결 상태 확인"""
        return self._notion_service and self._notion_service.is_connected()

    def _determine_operation(self, input: AgentInput) -> str:
        """입력에서 작업 유형 결정"""
        content = input.content.lower()
        metadata = input.metadata or {}

        # 메타데이터에서 명시적 작업 유형
        if "operation" in metadata:
            return metadata["operation"]

        # 내용에서 추론
        if any(word in content for word in ["생성", "만들", "create", "write"]):
            return "create"
        elif any(word in content for word in ["수정", "업데이트", "update", "edit"]):
            return "update"
        elif any(word in content for word in ["삭제", "보관", "archive", "delete"]):
            return "archive"
        elif any(word in content for word in ["읽", "조회", "read", "get"]):
            return "read"
        elif any(word in content for word in ["검색", "찾", "search", "find"]):
            return "search"
        elif any(word in content for word in ["목록", "리스트", "list"]):
            return "list"

        return "search"  # 기본값

    def _build_operation_request(
        self,
        operation: str,
        input_data: AgentInput,
        metadata: Dict[str, Any]
    ) -> MCPOperationRequest:
        """MCP 작업 요청 생성"""
        op_type = {
            "read": MCPOperationType.READ,
            "search": MCPOperationType.SEARCH,
            "list": MCPOperationType.LIST,
            "create": MCPOperationType.CREATE,
            "update": MCPOperationType.UPDATE,
            "archive": MCPOperationType.DELETE,
        }.get(operation, MCPOperationType.SEARCH)

        return MCPOperationRequest(
            agentId=self.id,
            service=MCPServiceType.NOTION,
            operation=op_type,
            target=MCPOperationTarget(
                type="page",
                id=metadata.get("page_id"),
                path=metadata.get("parent_path")
            ),
            payload=metadata.get("payload", {"query": input_data.content}),
            requiresApproval=op_type in [
                MCPOperationType.CREATE,
                MCPOperationType.UPDATE,
                MCPOperationType.DELETE
            ]
        )

    def _parse_operation_from_description(
        self,
        description: str,
        context: Dict[str, Any]
    ) -> str:
        """작업 설명에서 작업 유형 파싱"""
        description_lower = description.lower()

        if any(word in description_lower for word in ["생성", "만들", "create", "write", "작성"]):
            return "create"
        elif any(word in description_lower for word in ["수정", "업데이트", "update", "edit"]):
            return "update"
        elif any(word in description_lower for word in ["삭제", "보관", "archive", "delete"]):
            return "archive"
        elif any(word in description_lower for word in ["읽", "조회", "read", "get", "가져"]):
            return "read"
        elif any(word in description_lower for word in ["검색", "찾", "search", "find"]):
            return "search"
        elif any(word in description_lower for word in ["목록", "리스트", "list"]):
            return "list"

        return context.get("default_operation", "search")

    async def _execute_operation(
        self,
        operation: str,
        description: str,
        context: Dict[str, Any]
    ) -> AgentResult:
        """작업 실행"""
        if operation == "read":
            page_id = context.get("page_id")
            if not page_id:
                return failed("페이지 ID가 필요합니다.")
            return await self.read_page(page_id)

        elif operation == "search":
            query = context.get("query", description)
            filters = context.get("filters")
            return await self.search_pages(query, filters)

        elif operation == "list":
            parent_path = context.get("parent_path")
            return await self.list_pages(parent_path)

        elif operation == "create":
            parent_path = context.get("parent_path", "/")
            title = context.get("title", "New Page")
            content = context.get("content", "")
            properties = context.get("properties")
            return await self.create_page(parent_path, title, content, properties)

        elif operation == "update":
            page_id = context.get("page_id")
            if not page_id:
                return failed("페이지 ID가 필요합니다.")
            title = context.get("title")
            content = context.get("content")
            properties = context.get("properties")
            return await self.update_page(page_id, title, content, properties)

        elif operation == "archive":
            page_id = context.get("page_id")
            if not page_id:
                return failed("페이지 ID가 필요합니다.")
            return await self.archive_page(page_id)

        else:
            return failed(f"지원하지 않는 작업: {operation}")

    def _log(self, level: str, message: str):
        """로그 출력"""
        print(f"[{self.name}] [{level.upper()}] {message}")


# 싱글톤 인스턴스 (필요 시 사용)
notion_mcp_agent = NotionMCPAgent()
