from typing import Dict, List, Optional
from .types import (
    IMCPService,
    MCPServiceType,
    MCPServiceConfig,
    MCPOperationRequest,
    MCPOperationResult,
    MCPValidationResult,
    MCPEventHandler,
)


class MCPServiceRegistry:
    """
    MCP 서비스 레지스트리
    
    모든 MCP 서비스 인스턴스를 관리합니다.
    """
    
    def __init__(self):
        self.services: Dict[MCPServiceType, IMCPService] = {}
        self.configs: Dict[MCPServiceType, MCPServiceConfig] = {}
        self.global_event_handlers: set = set()
    
    def register(self, service: IMCPService, config: MCPServiceConfig) -> None:
        """서비스 등록"""
        self.services[service.type] = service
        self.configs[service.type] = config
        print(f"[MCPRegistry] Service registered: {service.name} ({service.type})")
    
    async def unregister(self, type: MCPServiceType) -> None:
        """서비스 해제"""
        service = self.services.get(type)
        if service and service.is_connected():
            await service.disconnect()
        self.services.pop(type, None)
        self.configs.pop(type, None)
        print(f"[MCPRegistry] Service unregistered: {type}")
    
    def get_service(self, type: MCPServiceType) -> Optional[IMCPService]:
        """서비스 조회"""
        return self.services.get(type)
    
    def get_all_services(self) -> List[IMCPService]:
        """모든 서비스 조회"""
        return list(self.services.values())
    
    def get_connected_services(self) -> List[IMCPService]:
        """연결된 서비스만 조회"""
        return [s for s in self.services.values() if s.is_connected()]
    
    async def connect_service(self, type: MCPServiceType) -> None:
        """서비스 연결"""
        service = self.services.get(type)
        if not service:
            raise ValueError(f"Service not found: {type}")
        await service.connect()
    
    async def connect_all(self) -> None:
        """모든 서비스 연결"""
        import asyncio
        
        enabled_services = [
            type for type, config in self.configs.items()
            if config.enabled
        ]
        
        async def connect_with_error_handling(service_type: MCPServiceType):
            try:
                await self.connect_service(service_type)
            except Exception as e:
                print(f"[MCPRegistry] Failed to connect {service_type}: {e}")
        
        await asyncio.gather(*[
            connect_with_error_handling(service_type)
            for service_type in enabled_services
        ], return_exceptions=True)
    
    async def disconnect_all(self) -> None:
        """모든 서비스 연결 해제"""
        import asyncio
        
        await asyncio.gather(*[
            service.disconnect()
            for service in self.services.values()
        ], return_exceptions=True)
    
    async def execute(self, request: MCPOperationRequest) -> MCPOperationResult:
        """작업 실행"""
        service = self.services.get(request.service)
        if not service:
            return MCPOperationResult(
                success=False,
                error=f"Service not found: {request.service}"
            )
        
        if not service.is_connected():
            return MCPOperationResult(
                success=False,
                error=f"Service not connected: {request.service}"
            )
        
        return await service.execute(request)
    
    async def validate(self, request: MCPOperationRequest) -> MCPValidationResult:
        """작업 검증"""
        service = self.services.get(request.service)
        if not service:
            return MCPValidationResult(
                isValid=False,
                errors=[f"Service not found: {request.service}"],
                warnings=[],
                requiresApproval=True
            )
        
        return await service.validate(request)
    
    def on_global_event(self, handler: MCPEventHandler) -> None:
        """전역 이벤트 핸들러 등록"""
        self.global_event_handlers.add(handler)
    
    def get_status(self) -> Dict[str, any]:
        """서비스 상태 요약"""
        services = [
            {
                "type": type,
                "name": service.name,
                "connected": service.is_connected(),
                "enabled": self.configs.get(type, MCPServiceConfig(
                    type=type,
                    name=service.name,
                    enabled=False
                )).enabled
            }
            for type, service in self.services.items()
        ]
        
        return {
            "total": len(services),
            "connected": len([s for s in services if s["connected"]]),
            "services": services
        }


# 싱글톤 인스턴스
mcp_registry = MCPServiceRegistry()

