import { agentRegistry } from './agents/index.js';
import { mcpRegistry } from './mcp/index.js';
import { NotionService, GmailService } from './mcp/index.js';
import { AgentMonitorWebSocketServer } from './websocket/WebSocketServer.js';

/**
 * Agent Monitor 서버 메인 엔트리포인트
 */
async function main() {
  console.log('='.repeat(50));
  console.log('Agent Monitor Server Starting...');
  console.log('='.repeat(50));

  // 1. MCP 서비스 등록
  console.log('\n[1/3] Registering MCP Services...');

  const notionService = new NotionService({
    type: 'notion',
    name: 'Notion Workspace',
    enabled: true,
    credentials: {
      apiKey: process.env.NOTION_API_KEY || 'demo-key',
    },
  });

  const gmailService = new GmailService({
    type: 'gmail',
    name: 'Gmail Account',
    enabled: true,
  });

  mcpRegistry.register(notionService, {
    type: 'notion',
    name: 'Notion Workspace',
    enabled: true,
  });

  mcpRegistry.register(gmailService, {
    type: 'gmail',
    name: 'Gmail Account',
    enabled: true,
  });

  console.log(`  - Registered: ${mcpRegistry.getStatus().total} services`);

  // 2. WebSocket 서버 시작
  console.log('\n[2/3] Starting WebSocket Server...');

  const wsPort = parseInt(process.env.WS_PORT || '8080');
  const wsServer = new AgentMonitorWebSocketServer(wsPort);

  // Agent 이벤트를 WebSocket으로 브로드캐스트
  agentRegistry.onGlobalEvent((event) => {
    switch (event.type) {
      case 'state_changed':
        if (event.payload && typeof event.payload === 'object' && 'id' in event.payload) {
          wsServer.broadcastAgentUpdate(event.payload as Parameters<typeof wsServer.broadcastAgentUpdate>[0]);
        }
        break;
      case 'ticket_created':
        wsServer.broadcastTicketCreated(event.payload as Parameters<typeof wsServer.broadcastTicketCreated>[0]);
        break;
      case 'approval_requested':
        wsServer.broadcastApprovalRequest(event.payload as Parameters<typeof wsServer.broadcastApprovalRequest>[0]);
        break;
      case 'log':
        // 로그는 브로드캐스트하지 않음 (필요시 추가)
        break;
    }
  });

  // 클라이언트 액션 처리
  wsServer.onClientAction = (clientId, message) => {
    console.log(`[Server] Client action from ${clientId}:`, message.type);

    // TODO: 실제 액션 처리 구현
    // - approve_request -> ApprovalService.approve()
    // - reject_request -> ApprovalService.reject()
    // - pause_agent -> agentRegistry.updateAgentState()
    // etc.
  };

  wsServer.start();
  console.log(`  - WebSocket server running on port ${wsPort}`);

  // 3. 초기화 완료
  console.log('\n[3/3] Server Ready!');
  console.log('='.repeat(50));
  console.log('Agent Monitor Server is running');
  console.log(`WebSocket: ws://localhost:${wsPort}`);
  console.log('='.repeat(50));

  // Graceful shutdown
  process.on('SIGINT', async () => {
    console.log('\nShutting down...');
    wsServer.stop();
    await mcpRegistry.disconnectAll();
    process.exit(0);
  });

  process.on('SIGTERM', async () => {
    console.log('\nShutting down...');
    wsServer.stop();
    await mcpRegistry.disconnectAll();
    process.exit(0);
  });
}

main().catch((error) => {
  console.error('Failed to start server:', error);
  process.exit(1);
});
