import { BaseMCPService } from '../BaseMCPService.js';
import type {
  MCPServiceConfig,
  MCPOperationRequest,
  MCPOperationResult,
} from '../types.js';

/**
 * Gmail MCP 서비스
 *
 * 허용 작업:
 * - 메일 읽기/검색
 * - 메일 초안 생성 (승인 필요)
 *
 * 금지 작업:
 * - 승인 없는 메일 발송 (send)
 * - 승인 없는 자동 답장
 */
export class GmailService extends BaseMCPService {
  constructor(config: MCPServiceConfig) {
    super({
      ...config,
      type: 'gmail',
    });
  }

  protected async doConnect(): Promise<void> {
    // TODO: 실제 Gmail API OAuth 연결
    console.log(`[GmailService] Connected to Gmail`);
  }

  protected async doDisconnect(): Promise<void> {
    console.log(`[GmailService] Disconnected from Gmail`);
  }

  protected async doExecute(request: MCPOperationRequest): Promise<MCPOperationResult> {
    const { operation, target, payload } = request;

    switch (operation) {
      case 'read':
        return this.readEmail(target.id!);

      case 'search':
        return this.searchEmails(payload as { query: string; maxResults?: number });

      case 'list':
        return this.listEmails(payload as { labelIds?: string[]; maxResults?: number });

      case 'create':
        return this.createDraft(payload as unknown as EmailDraft);

      case 'update':
        return this.updateDraft(target.id!, payload as unknown as Partial<EmailDraft>);

      case 'send':
        return this.sendEmail(target.id!, payload as unknown as EmailDraft);

      case 'delete':
        return this.deleteEmail(target.id!);

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
      case 'read':
      case 'delete':
        if (!request.target?.id) {
          errors.push('Email ID is required');
        }
        break;

      case 'create':
      case 'send': {
        const draft = request.payload as unknown as EmailDraft;
        if (!draft?.to || draft.to.length === 0) {
          errors.push('At least one recipient is required');
        }
        if (!draft?.subject) {
          warnings.push('Email subject is recommended');
        }
        if (!draft?.body) {
          warnings.push('Email body is empty');
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

    // 발송 작업에 대한 추가 경고
    if (request.operation === 'send') {
      warnings.push('메일이 실제로 발송됩니다. 내용을 다시 확인해주세요.');
    }

    return { errors, warnings };
  }

  protected shouldRequireApproval(request: MCPOperationRequest): boolean {
    // Gmail에서는 모든 쓰기 작업에 승인 필요
    // 특히 send는 무조건 필수 (APPROVAL_REQUIRED_OPERATIONS에 포함)
    return ['create', 'update', 'send'].includes(request.operation);
  }

  // === Gmail API 작업 구현 ===

  private async readEmail(emailId: string): Promise<MCPOperationResult> {
    console.log(`[GmailService] Reading email: ${emailId}`);
    return {
      success: true,
      data: {
        id: emailId,
        from: 'sender@example.com',
        to: ['recipient@example.com'],
        subject: 'Sample Email',
        body: '이메일 내용...',
        date: new Date().toISOString(),
      },
    };
  }

  private async searchEmails(params: {
    query: string;
    maxResults?: number;
  }): Promise<MCPOperationResult> {
    console.log(`[GmailService] Searching emails: ${params.query}`);
    return {
      success: true,
      data: {
        results: [],
        hasMore: false,
      },
    };
  }

  private async listEmails(params: {
    labelIds?: string[];
    maxResults?: number;
  }): Promise<MCPOperationResult> {
    console.log(`[GmailService] Listing emails`, params);
    return {
      success: true,
      data: {
        emails: [],
        nextPageToken: null,
      },
    };
  }

  private async createDraft(draft: EmailDraft): Promise<MCPOperationResult> {
    console.log(`[GmailService] Creating draft to: ${draft.to.join(', ')}`);
    return {
      success: true,
      data: {
        id: 'draft-id',
        ...draft,
        status: 'draft',
      },
      metadata: {
        message: '초안이 생성되었습니다. 발송하려면 승인이 필요합니다.',
      },
    };
  }

  private async updateDraft(
    draftId: string,
    updates: Partial<EmailDraft>
  ): Promise<MCPOperationResult> {
    console.log(`[GmailService] Updating draft: ${draftId}`);
    return {
      success: true,
      data: {
        id: draftId,
        ...updates,
        status: 'draft',
      },
    };
  }

  private async sendEmail(
    draftId: string | undefined,
    email: EmailDraft
  ): Promise<MCPOperationResult> {
    console.log(`[GmailService] Sending email to: ${email.to.join(', ')}`);
    return {
      success: true,
      data: {
        id: draftId || 'sent-email-id',
        ...email,
        status: 'sent',
        sentAt: new Date().toISOString(),
      },
      metadata: {
        message: '이메일이 발송되었습니다.',
      },
    };
  }

  private async deleteEmail(emailId: string): Promise<MCPOperationResult> {
    console.log(`[GmailService] Deleting email: ${emailId}`);
    return {
      success: true,
      data: {
        id: emailId,
        deleted: true,
      },
    };
  }
}

// 이메일 초안 타입
interface EmailDraft {
  to: string[];
  cc?: string[];
  bcc?: string[];
  subject: string;
  body: string;
  isHtml?: boolean;
  attachments?: Array<{
    filename: string;
    content: string;
    mimeType: string;
  }>;
}
