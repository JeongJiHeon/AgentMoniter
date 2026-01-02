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

# Import event store for event replay functionality
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.event_store import event_store


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
        self.event_store = event_store  # Use Redis event store for persistence
        self._recent_tasks: Dict[str, dict] = {}  # 최근 Task 저장소
    
    async def start(self) -> None:
        """서버 시작"""
        self.server = await websockets.serve(
            self._handle_connection,
            "0.0.0.0",
            self.port,
            ping_interval=20,  # 20초마다 ping
            ping_timeout=60,   # 60초 응답 대기
            close_timeout=10   # 연결 종료 대기
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
    
    async def _handle_connection(self, websocket: WebSocketServerProtocol) -> None:
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

        # 🆕 Event replay: Send recent events from Redis
        # agent_log 이벤트는 제외 (task별로 요청 시에만 전송)
        try:
            # Check if client has cursor (reconnection)
            cursor = await self.event_store.redis_service.get_client_cursor(client_id)

            if cursor:
                # Reconnection: Replay missed events
                print(f"[WebSocket] Client {client_id} reconnected, replaying events since {cursor}")
                missed_events = await self.event_store.get_events_since(float(cursor), limit=1000)
                # agent_log 제외 (task별 요청으로 처리)
                filtered_events = [e for e in missed_events if e.get("type") != "agent_log"]
                print(f"[WebSocket] Replaying {len(filtered_events)} missed events (excluded agent_log)")

                for event in filtered_events:
                    await self._send_to_client(client_id, WebSocketMessage(
                        type=event.get("type", "unknown"),
                        payload=event.get("payload", {}),
                        timestamp=datetime.fromisoformat(event.get("timestamp"))
                    ))
            else:
                # New connection: Send recent events (last 100)
                # agent_log 제외 - task details 패널에서 task별로 요청
                print(f"[WebSocket] New client {client_id}, sending recent events")
                recent_events = await self.event_store.get_recent_events(count=100)
                # agent_log 제외 (task별 요청으로 처리)
                filtered_events = [e for e in recent_events if e.get("type") != "agent_log"]
                print(f"[WebSocket] Sending {len(filtered_events)} recent events (excluded agent_log)")

                for event in filtered_events:
                    await self._send_to_client(client_id, WebSocketMessage(
                        type=event.get("type", "unknown"),
                        payload=event.get("payload", {}),
                        timestamp=datetime.fromisoformat(event.get("timestamp"))
                    ))
        except Exception as e:
            print(f"[WebSocket] Event replay error: {e}")
        
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
            # 연결 해제 로그는 디버그 시에만 필요
    
    async def _handle_message(self, client_id: str, message: WebSocketMessage) -> None:
        """메시지 처리"""
        print(f"[WebSocket] Message from {client_id}: {message.type}")

        try:
            # Task별 이벤트 요청 처리
            if message.type == "request_task_events":
                await self._handle_request_task_events(client_id, message.payload)
                return

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
                WebSocketMessageType.TASK_INTERACTION_CLIENT,
                WebSocketMessageType.CHAT_MESSAGE,
                WebSocketMessageType.UPDATE_LLM_CONFIG,
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

    async def _handle_request_task_events(self, client_id: str, payload: dict) -> None:
        """
        Task별 이벤트 요청 처리

        클라이언트가 특정 task의 이벤트만 요청할 때 사용
        이전 task의 로그가 섞이지 않도록 task_id로 필터링
        """
        task_id = payload.get("taskId") or payload.get("task_id")
        if not task_id:
            print(f"[WebSocket] request_task_events: No task_id provided")
            return

        try:
            # Task별 이벤트 조회
            task_events = await self.event_store.get_task_events(task_id)
            print(f"[WebSocket] Sending {len(task_events)} events for task {task_id}")

            # 클라이언트에 task_events_response 전송
            await self._send_to_client(client_id, WebSocketMessage(
                type="task_events_response",
                payload={
                    "taskId": task_id,
                    "events": task_events,
                    "count": len(task_events)
                }
            ))
        except Exception as e:
            print(f"[WebSocket] Error fetching task events: {e}")
            await self._send_to_client(client_id, WebSocketMessage(
                type="task_events_response",
                payload={
                    "taskId": task_id,
                    "events": [],
                    "count": 0,
                    "error": str(e)
                }
            ))
    
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
        asyncio.create_task(self._broadcast_with_store(
            WebSocketMessageType.AGENT_UPDATE,
            agent.model_dump(mode="json")
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
    
    def broadcast_agent_log(self, agent_id: str, agent_name: str, log_type: str, message: str, details: str = None, task_id: str = None) -> None:
        """Agent 로그 브로드캐스트 (Event Store에 저장)"""
        from uuid import uuid4
        from datetime import datetime

        log_message = {
            "id": str(uuid4()),
            "agentId": agent_id,
            "agentName": agent_name,
            "type": log_type,  # 'info', 'decision', 'warning', 'error'
            "message": message,
            "details": details,
            "relatedTaskId": task_id,
            "timestamp": datetime.now().isoformat()
        }

        print(f"[WebSocket] Broadcasting agent_log: {agent_name} - {log_type} - {message[:50]}... (taskId: {task_id})")

        # 🔴 Event Store에 저장 후 broadcast (클라이언트가 없어도 저장됨)
        asyncio.create_task(self._broadcast_with_store(
            message_type="agent_log",
            payload=log_message
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
            
            # 🆕 Task를 저장소에 저장 (재연결 시 복구용)
            task_id = task_dict.get('id')
            if task_id:
                self._recent_tasks[task_id] = task_dict
            
            print(f"[WebSocket] Broadcasting task_created: {task_dict.get('title', 'Unknown')}")
            
            self._broadcast(WebSocketMessage(
                type="task_created",
                payload=task_dict
            ))
        except Exception as e:
            print(f"[WebSocket] Error broadcasting task_created: {e}")
            import traceback
            traceback.print_exc()
    
    def update_task_status(self, task_id: str, status: str) -> None:
        """Task 상태 업데이트 (저장소 동기화)"""
        if task_id in self._recent_tasks:
            self._recent_tasks[task_id]['status'] = status
    
    def remove_task(self, task_id: str) -> None:
        """완료된 Task 저장소에서 제거"""
        if task_id in self._recent_tasks:
            del self._recent_tasks[task_id]
    
    def broadcast_task_interaction(self, task_id: str, role: str, message: str, agent_id: str = None, agent_name: str = None) -> None:
        """Task 상호작용 메시지 브로드캐스트 (Event Store에 저장)"""
        from uuid import uuid4
        from datetime import datetime

        interaction_message = {
            "id": str(uuid4()),
            "taskId": task_id,
            "role": role,  # 'user' or 'agent'
            "message": message,
            "agentId": agent_id,
            "agentName": agent_name,
            "timestamp": datetime.now().isoformat()
        }

        print(f"[WebSocket] Broadcasting task_interaction: taskId={task_id}, role={role}, message={message[:50]}...")

        # 🔴 Event Store에 저장 후 broadcast (클라이언트가 없어도 저장됨)
        asyncio.create_task(self._broadcast_with_store(
            message_type=WebSocketMessageType.TASK_INTERACTION,
            payload=interaction_message
        ))
    
    def broadcast_chat_message(self, role: str, content: str, agent_id: str = None, agent_name: str = None) -> None:
        """Chat 메시지 브로드캐스트 (Orchestration Agent 응답)"""
        from uuid import uuid4
        from datetime import datetime
        
        chat_message = {
            "id": str(uuid4()),
            "role": role,  # 'assistant' or 'user'
            "content": content,
            "agentId": agent_id,
            "agentName": agent_name,
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"[WebSocket] Broadcasting chat_message_response: role={role}, content={content[:50]}...")
        
        self._broadcast(WebSocketMessage(
            type=WebSocketMessageType.CHAT_MESSAGE_RESPONSE,
            payload=chat_message
        ))
    
    def broadcast_message(self, message_dict: dict) -> None:
        """일반 메시지 브로드캐스트 (type, payload 포함)"""
        msg_type = message_dict.get('type', 'unknown')
        payload = message_dict.get('payload', {})

        print(f"[WebSocket] Broadcasting message: {msg_type}")

        self._broadcast(WebSocketMessage(
            type=msg_type,
            payload=payload
        ))

    # === Task/Agent 상태 브로드캐스트 (TaskStateManager 연동) ===

    def broadcast_task_status_change(self, event: dict) -> None:
        """Task 상태 변경 브로드캐스트"""
        print(f"[WebSocket] Broadcasting task_status_change: {event.get('task_id')} -> {event.get('new_status')}")

        asyncio.create_task(self._broadcast_with_store(
            message_type="task_status_change",
            payload=event
        ))

    def broadcast_agent_status_change(self, agent_status: dict) -> None:
        """Agent 상태 변경 브로드캐스트"""
        print(f"[WebSocket] Broadcasting agent_status_change: {agent_status.get('agent_name')} -> {agent_status.get('status')}")

        asyncio.create_task(self._broadcast_with_store(
            message_type="agent_status_change",
            payload=agent_status
        ))

    def broadcast_task_summary(self, summary: dict) -> None:
        """전체 Task 상태 요약 브로드캐스트"""
        print(f"[WebSocket] Broadcasting task_summary: running={summary.get('counts', {}).get('running', 0)}")

        self._broadcast(WebSocketMessage(
            type="task_summary",
            payload=summary
        ))

    def broadcast_agent_summary(self, summary: dict) -> None:
        """전체 Agent 상태 요약 브로드캐스트"""
        print(f"[WebSocket] Broadcasting agent_summary: running={summary.get('counts', {}).get('running', 0)}")

        self._broadcast(WebSocketMessage(
            type="agent_summary",
            payload=summary
        ))

    # === 유틸리티 ===
    
    async def _broadcast_with_store(self, message_type: str, payload: dict) -> None:
        """
        🔴 Message Queueing Logic:
        1. Store event to Redis FIRST (even if no clients connected)
        2. Broadcast to connected clients (if any)
        3. Update client cursors

        This ensures:
        - Messages are never lost
        - Reconnected clients receive missed messages via event replay
        """
        try:
            # 1. Store to Redis event store (ALWAYS, even if no clients)
            timestamp = await self.event_store.store_event(message_type, payload)

            if not self.clients:
                print(f"[WebSocket] No clients connected, message stored to Event Store (will be replayed on reconnect)")
                return

            # 2. Broadcast to connected clients
            message = WebSocketMessage(type=message_type, payload=payload)
            self._broadcast(message)

            # 3. Update client cursors (so they know what events they've received)
            for client_id in self.clients.keys():
                try:
                    await self.event_store.redis_service.save_client_cursor(client_id, str(timestamp))
                except Exception as e:
                    print(f"[WebSocket] Failed to save cursor for client {client_id}: {e}")

        except Exception as e:
            print(f"[WebSocket] _broadcast_with_store error: {e}")
            import traceback
            traceback.print_exc()
            # Fallback: still broadcast even if Redis fails
            if self.clients:
                message = WebSocketMessage(type=message_type, payload=payload)
                self._broadcast(message)

    def _broadcast(self, message: WebSocketMessage) -> None:
        """모든 클라이언트에 브로드캐스트 (internal use only)"""
        if not self.clients:
            print(f"[WebSocket] WARNING: No clients connected, cannot broadcast {message.type}")
            return

        data = json.dumps(message.to_dict())
        disconnected = []
        sent_count = 0

        for client_id, client in self.clients.items():
            try:
                asyncio.create_task(client.websocket.send(data))
                sent_count += 1
            except Exception as e:
                print(f"[WebSocket] Failed to send to {client_id}: {e}")
                disconnected.append(client_id)

        for client_id in disconnected:
            if client_id in self.clients:
                del self.clients[client_id]
        
        if disconnected:
            print(f"[WebSocket] Removed {len(disconnected)} disconnected clients")
    
    async def _send_to_client(self, client_id: str, message: WebSocketMessage) -> None:
        """특정 클라이언트에 메시지 전송"""
        client = self.clients.get(client_id)
        if client:
            try:
                await client.websocket.send(json.dumps(message.to_dict()))
            except Exception:
                pass  # 클라이언트가 이미 연결 해제된 경우 무시
    
    def get_client_count(self) -> int:
        """연결된 클라이언트 수"""
        return len(self.clients)

