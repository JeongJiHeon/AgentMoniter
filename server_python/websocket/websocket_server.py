import asyncio
import json
from typing import Dict, Set, Optional, Callable, Any
from datetime import datetime
from uuid import uuid4
import websockets
from websockets.server import WebSocketServerProtocol
from models.agent import Agent
from models.ticket import Ticket
from models.approval import ApprovalRequest
from models.websocket import WebSocketMessageType


class WebSocketClient:
    def __init__(self, client_id: str, websocket: WebSocketServerProtocol):
        self.id = client_id
        self.websocket = websocket
        self.is_alive = True
    
    async def pong_received(self):
        """Pong 응답 수신 시 호출"""
        self.is_alive = True


class WebSocketMessage:
    def __init__(self, type: str, payload: Any, timestamp: Optional[datetime] = None):
        self.type = type
        self.payload = payload
        self.timestamp = timestamp or datetime.now()
    
    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat()
        }


class AgentMonitorWebSocketServer:
    """
    WebSocket 서버
    
    프론트엔드 모니터링 UI와 실시간 통신
    """
    
    def __init__(self, port: int = 8080):
        self.port = port
        self.clients: Dict[str, WebSocketClient] = {}
        self.server: Optional[websockets.server.Serve] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.on_client_action: Optional[Callable[[str, WebSocketMessage], None]] = None
    
    async def start(self) -> None:
        """서버 시작"""
        self.server = await websockets.serve(
            self._handle_connection,
            "0.0.0.0",
            self.port
        )
        
        # Heartbeat 시작
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        print(f"[WebSocket] Server started on port {self.port}")
    
    async def stop(self) -> None:
        """서버 중지"""
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # 모든 클라이언트 연결 종료
        for client in list(self.clients.values()):
            await client.websocket.close()
        self.clients.clear()
        
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        print("[WebSocket] Server stopped")
    
    async def _handle_connection(self, websocket: WebSocketServerProtocol, path: str) -> None:
        """클라이언트 연결 처리"""
        client_id = str(uuid4())
        client = WebSocketClient(client_id, websocket)
        self.clients[client_id] = client
        
        print(f"[WebSocket] Client connected: {client_id}")
        
        # 연결 확인 메시지
        await self._send_to_client(client_id, WebSocketMessage(
            type=WebSocketMessageType.SYSTEM_NOTIFICATION,
            payload={"message": "Connected to Agent Monitor"}
        ))
        
        # 등록된 모든 Agent 상태 전송
        from agents import agent_registry
        all_agents = agent_registry.get_all_agent_states()
        print(f"[WebSocket] Sending {len(all_agents)} registered agents to client {client_id}")
        for agent in all_agents:
            await self._send_to_client(client_id, WebSocketMessage(
                type=WebSocketMessageType.AGENT_UPDATE,
                payload=agent.model_dump(mode="json") if hasattr(agent, 'model_dump') else agent
            ))
        
        try:
            # Pong 핸들러 설정
            async def pong_handler():
                client.is_alive = True
            
            async for message in websocket:
                try:
                    # Pong 메시지 처리
                    if isinstance(message, type(None)) or message == b'':
                        await pong_handler()
                        continue
                    
                    if isinstance(message, bytes):
                        message = message.decode('utf-8')
                    
                    data = json.loads(message)
                    ws_message = WebSocketMessage(
                        type=data.get("type"),
                        payload=data.get("payload"),
                        timestamp=datetime.fromisoformat(data.get("timestamp")) if data.get("timestamp") else datetime.now()
                    )
                    await self._handle_message(client_id, ws_message)
                except json.JSONDecodeError as e:
                    print(f"[WebSocket] Failed to parse message: {e}")
                except Exception as e:
                    print(f"[WebSocket] Error handling message: {e}")
                    import traceback
                    traceback.print_exc()
                    # 메시지 처리 중 에러가 발생해도 연결은 유지
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            print(f"[WebSocket] Connection error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if client_id in self.clients:
                del self.clients[client_id]
            print(f"[WebSocket] Client disconnected: {client_id}")
    
    async def _handle_message(self, client_id: str, message: WebSocketMessage) -> None:
        """메시지 처리"""
        print(f"[WebSocket] Message from {client_id}: {message.type}")

        try:
            # 클라이언트 -> 서버 메시지 처리
            if message.type in [
                WebSocketMessageType.ASSIGN_TASK,
                WebSocketMessageType.CREATE_AGENT,
                WebSocketMessageType.APPROVE_REQUEST,
                WebSocketMessageType.REJECT_REQUEST,
                WebSocketMessageType.SELECT_OPTION,
                WebSocketMessageType.PROVIDE_INPUT,
                WebSocketMessageType.PAUSE_AGENT,
                WebSocketMessageType.RESUME_AGENT,
                WebSocketMessageType.CANCEL_TICKET,
            ]:
                if self.on_client_action:
                    await self.on_client_action(client_id, message)
            else:
                print(f"[WebSocket] Unknown message type: {message.type}")
        except Exception as e:
            print(f"[WebSocket] Error in _handle_message: {e}")
            import traceback
            traceback.print_exc()
            # 에러가 발생해도 연결은 유지
    
    async def _heartbeat_loop(self) -> None:
        """Heartbeat 체크 (30초마다)"""
        while True:
            try:
                await asyncio.sleep(30)
                
                disconnected = []
                for client_id, client in list(self.clients.items()):
                    if not client.is_alive:
                        try:
                            await client.websocket.close()
                        except Exception:
                            pass
                        disconnected.append(client_id)
                    else:
                        client.is_alive = False
                        try:
                            pong_waiter = await client.websocket.ping()
                            # pong 응답을 기다리지 않고 바로 다음으로 진행
                            # 실제로는 pong이 오면 is_alive가 True로 설정되어야 함
                        except Exception:
                            disconnected.append(client_id)
                
                for client_id in disconnected:
                    if client_id in self.clients:
                        del self.clients[client_id]
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[WebSocket] Heartbeat error: {e}")
    
    # === 브로드캐스트 메서드 ===
    
    def broadcast_agent_update(self, agent: Agent) -> None:
        """Agent 상태 업데이트 브로드캐스트"""
        self._broadcast(WebSocketMessage(
            type=WebSocketMessageType.AGENT_UPDATE,
            payload=agent.model_dump(mode="json")
        ))
    
    def broadcast_ticket_created(self, ticket: Ticket) -> None:
        """티켓 생성 브로드캐스트"""
        self._broadcast(WebSocketMessage(
            type=WebSocketMessageType.TICKET_CREATED,
            payload=ticket.model_dump(mode="json")
        ))
    
    def broadcast_ticket_updated(self, ticket: Ticket) -> None:
        """티켓 업데이트 브로드캐스트"""
        self._broadcast(WebSocketMessage(
            type=WebSocketMessageType.TICKET_UPDATED,
            payload=ticket.model_dump(mode="json")
        ))
    
    def broadcast_approval_request(self, request: ApprovalRequest) -> None:
        """승인 요청 브로드캐스트"""
        self._broadcast(WebSocketMessage(
            type=WebSocketMessageType.APPROVAL_REQUEST,
            payload=request.model_dump(mode="json")
        ))
    
    def broadcast_approval_resolved(self, request: ApprovalRequest) -> None:
        """승인 완료 브로드캐스트"""
        self._broadcast(WebSocketMessage(
            type=WebSocketMessageType.APPROVAL_RESOLVED,
            payload=request.model_dump(mode="json")
        ))
    
    def broadcast_notification(self, message: str, level: str = "info") -> None:
        """시스템 알림 브로드캐스트"""
        self._broadcast(WebSocketMessage(
            type=WebSocketMessageType.SYSTEM_NOTIFICATION,
            payload={"message": message, "level": level}
        ))
    
    def broadcast_task_created(self, task) -> None:
        """Task 생성 브로드캐스트"""
        try:
            # Task 객체를 딕셔너리로 변환
            if hasattr(task, 'model_dump'):
                task_dict = task.model_dump(mode="json")
            elif hasattr(task, 'dict'):
                task_dict = task.dict()
            elif isinstance(task, dict):
                task_dict = task
            else:
                # Pydantic 모델을 dict로 변환
                task_dict = {
                    "id": getattr(task, 'id', None),
                    "title": getattr(task, 'title', None),
                    "description": getattr(task, 'description', None),
                    "status": getattr(task, 'status', None),
                    "priority": getattr(task, 'priority', None),
                    "source": getattr(task, 'source', None),
                    "sourceReference": getattr(task, 'sourceReference', None),
                    "tags": getattr(task, 'tags', []),
                    "createdAt": getattr(task, 'createdAt', None).isoformat() if hasattr(task, 'createdAt') and task.createdAt else None,
                    "updatedAt": getattr(task, 'updatedAt', None).isoformat() if hasattr(task, 'updatedAt') and task.updatedAt else None,
                    "completedAt": getattr(task, 'completedAt', None).isoformat() if hasattr(task, 'completedAt') and task.completedAt else None,
                }
            
            print(f"[WebSocket] Broadcasting task_created: {task_dict.get('title', 'Unknown')}")
            print(f"[WebSocket] Active clients: {len(self.clients)}")
            
            self._broadcast(WebSocketMessage(
                type="task_created",
                payload=task_dict
            ))
        except Exception as e:
            print(f"[WebSocket] Error broadcasting task_created: {e}")
            import traceback
            traceback.print_exc()
    
    # === 유틸리티 ===
    
    def _broadcast(self, message: WebSocketMessage) -> None:
        """모든 클라이언트에 브로드캐스트"""
        data = json.dumps(message.to_dict())
        disconnected = []
        
        for client_id, client in self.clients.items():
            try:
                if client.websocket.open:
                    asyncio.create_task(client.websocket.send(data))
            except Exception:
                disconnected.append(client_id)
        
        for client_id in disconnected:
            if client_id in self.clients:
                del self.clients[client_id]
    
    async def _send_to_client(self, client_id: str, message: WebSocketMessage) -> None:
        """특정 클라이언트에 메시지 전송"""
        client = self.clients.get(client_id)
        if client and client.websocket.open:
            try:
                await client.websocket.send(json.dumps(message.to_dict()))
            except Exception as e:
                print(f"[WebSocket] Failed to send to client {client_id}: {e}")
    
    def get_client_count(self) -> int:
        """연결된 클라이언트 수"""
        return len(self.clients)

