import { WebSocketServer as WSServer, WebSocket } from 'ws';
import { v4 as uuidv4 } from 'uuid';
import type { Agent, Ticket, ApprovalRequest, WebSocketMessageType } from '../models/index.js';

interface WebSocketClient {
  id: string;
  ws: WebSocket;
  isAlive: boolean;
}

interface WebSocketMessage {
  type: WebSocketMessageType;
  payload: unknown;
  timestamp: Date;
}

/**
 * WebSocket 서버
 *
 * 프론트엔드 모니터링 UI와 실시간 통신
 */
export class AgentMonitorWebSocketServer {
  private wss: WSServer | null = null;
  private clients: Map<string, WebSocketClient> = new Map();
  private heartbeatInterval: ReturnType<typeof setInterval> | null = null;

  constructor(private port: number = 8080) {}

  /**
   * 서버 시작
   */
  start(): void {
    this.wss = new WSServer({ port: this.port });

    this.wss.on('connection', (ws) => {
      const clientId = uuidv4();
      const client: WebSocketClient = {
        id: clientId,
        ws,
        isAlive: true,
      };

      this.clients.set(clientId, client);
      console.log(`[WebSocket] Client connected: ${clientId}`);

      // 연결 확인 메시지
      this.sendToClient(clientId, {
        type: 'system_notification',
        payload: { message: 'Connected to Agent Monitor' },
        timestamp: new Date(),
      });

      // 메시지 핸들링
      ws.on('message', (data) => {
        try {
          const message = JSON.parse(data.toString()) as WebSocketMessage;
          this.handleMessage(clientId, message);
        } catch (error) {
          console.error(`[WebSocket] Failed to parse message:`, error);
        }
      });

      // Heartbeat
      ws.on('pong', () => {
        client.isAlive = true;
      });

      // 연결 종료
      ws.on('close', () => {
        this.clients.delete(clientId);
        console.log(`[WebSocket] Client disconnected: ${clientId}`);
      });

      // 에러 처리
      ws.on('error', (error) => {
        console.error(`[WebSocket] Client error (${clientId}):`, error);
      });
    });

    // Heartbeat 체크 (30초마다)
    this.heartbeatInterval = setInterval(() => {
      this.clients.forEach((client, clientId) => {
        if (!client.isAlive) {
          client.ws.terminate();
          this.clients.delete(clientId);
          return;
        }
        client.isAlive = false;
        client.ws.ping();
      });
    }, 30000);

    console.log(`[WebSocket] Server started on port ${this.port}`);
  }

  /**
   * 서버 중지
   */
  stop(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
    }

    this.clients.forEach((client) => {
      client.ws.close();
    });
    this.clients.clear();

    this.wss?.close();
    this.wss = null;

    console.log(`[WebSocket] Server stopped`);
  }

  /**
   * 메시지 처리
   */
  private handleMessage(clientId: string, message: WebSocketMessage): void {
    console.log(`[WebSocket] Message from ${clientId}:`, message.type);

    // 클라이언트 -> 서버 메시지 처리
    switch (message.type) {
      case 'approve_request':
      case 'reject_request':
      case 'select_option':
      case 'provide_input':
        // 이벤트 발생 (외부에서 처리)
        this.onClientAction?.(clientId, message);
        break;

      case 'pause_agent':
      case 'resume_agent':
      case 'cancel_ticket':
        this.onClientAction?.(clientId, message);
        break;

      default:
        console.log(`[WebSocket] Unknown message type: ${message.type}`);
    }
  }

  // === 브로드캐스트 메서드 ===

  /**
   * Agent 상태 업데이트 브로드캐스트
   */
  broadcastAgentUpdate(agent: Agent): void {
    this.broadcast({
      type: 'agent_update',
      payload: agent,
      timestamp: new Date(),
    });
  }

  /**
   * 티켓 생성 브로드캐스트
   */
  broadcastTicketCreated(ticket: Ticket): void {
    this.broadcast({
      type: 'ticket_created',
      payload: ticket,
      timestamp: new Date(),
    });
  }

  /**
   * 티켓 업데이트 브로드캐스트
   */
  broadcastTicketUpdated(ticket: Ticket): void {
    this.broadcast({
      type: 'ticket_updated',
      payload: ticket,
      timestamp: new Date(),
    });
  }

  /**
   * 승인 요청 브로드캐스트
   */
  broadcastApprovalRequest(request: ApprovalRequest): void {
    this.broadcast({
      type: 'approval_request',
      payload: request,
      timestamp: new Date(),
    });
  }

  /**
   * 승인 완료 브로드캐스트
   */
  broadcastApprovalResolved(request: ApprovalRequest): void {
    this.broadcast({
      type: 'approval_resolved',
      payload: request,
      timestamp: new Date(),
    });
  }

  /**
   * 시스템 알림 브로드캐스트
   */
  broadcastNotification(message: string, level: 'info' | 'warning' | 'error' = 'info'): void {
    this.broadcast({
      type: 'system_notification',
      payload: { message, level },
      timestamp: new Date(),
    });
  }

  // === 유틸리티 ===

  private broadcast(message: WebSocketMessage): void {
    const data = JSON.stringify(message);
    this.clients.forEach((client) => {
      if (client.ws.readyState === WebSocket.OPEN) {
        client.ws.send(data);
      }
    });
  }

  private sendToClient(clientId: string, message: WebSocketMessage): void {
    const client = this.clients.get(clientId);
    if (client?.ws.readyState === WebSocket.OPEN) {
      client.ws.send(JSON.stringify(message));
    }
  }

  /**
   * 연결된 클라이언트 수
   */
  getClientCount(): number {
    return this.clients.size;
  }

  // === 이벤트 핸들러 (외부에서 설정) ===

  onClientAction?: (clientId: string, message: WebSocketMessage) => void;
}
