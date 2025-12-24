import { BaseMCPService } from '../BaseMCPService.js';
import type {
  MCPServiceConfig,
  MCPOperationRequest,
  MCPOperationResult,
} from '../types.js';

/**
 * Slack MCP 서비스
 *
 * 허용 작업:
 * - 메시지 읽기/검색
 * - 채널 목록 조회
 * - 메시지 초안 생성 (승인 필요)
 *
 * 금지 작업:
 * - 승인 없는 메시지 발송
 * - 승인 없는 채널 생성/삭제
 */
export class SlackService extends BaseMCPService {
  private botToken?: string;
  private webhookUrl?: string;

  constructor(config: MCPServiceConfig) {
    super({
      ...config,
      type: 'slack',
    });
    this.botToken = config.credentials?.accessToken;
    this.webhookUrl = config.credentials?.webhookUrl;
  }

  protected async doConnect(): Promise<void> {
    if (!this.botToken) {
      throw new Error('Slack Bot Token is required');
    }
    console.log(`[SlackService] Connected to Slack`);
  }

  protected async doDisconnect(): Promise<void> {
    console.log(`[SlackService] Disconnected from Slack`);
  }

  protected async doExecute(request: MCPOperationRequest): Promise<MCPOperationResult> {
    const { operation, target, payload } = request;

    switch (operation) {
      case 'read':
        return this.readMessage(target.id!);

      case 'search':
        return this.searchMessages(payload as unknown as { query: string });

      case 'list':
        if (target.type === 'channel') {
          return this.listChannels();
        }
        return this.listMessages(target.id!);

      case 'create':
        return this.createMessageDraft(payload as unknown as SlackMessage);

      case 'send':
        return this.sendMessage(payload as unknown as SlackMessage);

      default:
        return {
          success: false,
          error: `Unsupported operation: ${operation}`,
        };
    }
  }

  protected async doValidate(request: MCPOperationRequest): Promise<{
    errors: string[];
    warnings: string[];
  }> {
    const errors: string[] = [];
    const warnings: string[] = [];

    switch (request.operation) {
      case 'create':
      case 'send': {
        const message = request.payload as unknown as SlackMessage;
        if (!message?.channel) {
          errors.push('Channel is required');
        }
        if (!message?.text && !message?.blocks) {
          errors.push('Message text or blocks required');
        }
        break;
      }

      case 'search': {
        const searchPayload = request.payload as { query?: string };
        if (!searchPayload?.query) {
          errors.push('Search query is required');
        }
        break;
      }
    }

    if (request.operation === 'send') {
      warnings.push('메시지가 실제로 발송됩니다. 내용을 확인해주세요.');
    }

    return { errors, warnings };
  }

  protected shouldRequireApproval(request: MCPOperationRequest): boolean {
    return ['create', 'send'].includes(request.operation);
  }

  // === Slack API 작업 구현 ===

  private async readMessage(messageTs: string): Promise<MCPOperationResult> {
    console.log(`[SlackService] Reading message: ${messageTs}`);
    return {
      success: true,
      data: {
        ts: messageTs,
        text: 'Sample message',
        user: 'U12345',
        channel: 'C12345',
      },
    };
  }

  private async searchMessages(params: { query: string }): Promise<MCPOperationResult> {
    console.log(`[SlackService] Searching messages: ${params.query}`);
    return {
      success: true,
      data: {
        messages: [],
        total: 0,
      },
    };
  }

  private async listChannels(): Promise<MCPOperationResult> {
    console.log(`[SlackService] Listing channels`);
    return {
      success: true,
      data: {
        channels: [],
      },
    };
  }

  private async listMessages(channelId: string): Promise<MCPOperationResult> {
    console.log(`[SlackService] Listing messages in channel: ${channelId}`);
    return {
      success: true,
      data: {
        messages: [],
        hasMore: false,
      },
    };
  }

  private async createMessageDraft(message: SlackMessage): Promise<MCPOperationResult> {
    console.log(`[SlackService] Creating message draft for channel: ${message.channel}`);
    return {
      success: true,
      data: {
        ...message,
        status: 'draft',
      },
      metadata: {
        message: '메시지 초안이 생성되었습니다. 발송하려면 승인이 필요합니다.',
      },
    };
  }

  private async sendMessage(message: SlackMessage): Promise<MCPOperationResult> {
    console.log(`[SlackService] Sending message to channel: ${message.channel}`);
    return {
      success: true,
      data: {
        ...message,
        ts: Date.now().toString(),
        status: 'sent',
      },
      metadata: {
        message: '메시지가 발송되었습니다.',
      },
    };
  }
}

interface SlackMessage {
  channel: string;
  text?: string;
  blocks?: unknown[];
  threadTs?: string;
  replyBroadcast?: boolean;
}
