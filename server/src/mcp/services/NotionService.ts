import { BaseMCPService } from '../BaseMCPService.js';
import type {
  MCPServiceConfig,
  MCPOperationRequest,
  MCPOperationResult,
} from '../types.js';

/**
 * Notion MCP 서비스
 *
 * 허용 작업:
 * - 페이지 읽기/검색
 * - 페이지 초안 생성 (승인 필요)
 * - 페이지 업데이트 (승인 필요)
 *
 * 금지 작업:
 * - 승인 없는 페이지 공개
 * - 승인 없는 공유 설정 변경
 */
export class NotionService extends BaseMCPService {
  private apiKey?: string;

  constructor(config: MCPServiceConfig) {
    super({
      ...config,
      type: 'notion',
    });
    this.apiKey = config.credentials?.apiKey;
  }

  protected async doConnect(): Promise<void> {
    if (!this.apiKey) {
      throw new Error('Notion API key is required');
    }

    // TODO: 실제 Notion API 연결 구현
    console.log(`[NotionService] Connected to Notion`);
  }

  protected async doDisconnect(): Promise<void> {
    console.log(`[NotionService] Disconnected from Notion`);
  }

  protected async doExecute(request: MCPOperationRequest): Promise<MCPOperationResult> {
    const { operation, target, payload } = request;

    switch (operation) {
      case 'read':
        return this.readPage(target.id!);

      case 'search':
        return this.searchPages(payload as { query: string });

      case 'list':
        return this.listPages(target.path);

      case 'create':
        return this.createPage(target.path!, payload as Record<string, unknown>);

      case 'update':
        return this.updatePage(target.id!, payload as Record<string, unknown>);

      case 'delete':
        return this.archivePage(target.id!);

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

    // 작업별 검증
    switch (request.operation) {
      case 'read':
      case 'update':
      case 'delete':
        if (!request.target?.id) {
          errors.push('Page ID is required');
        }
        break;

      case 'create':
        if (!request.target?.path) {
          errors.push('Parent page path is required');
        }
        if (!request.payload?.title) {
          warnings.push('Page title is recommended');
        }
        break;

      case 'search':
        if (!(request.payload as { query?: string })?.query) {
          errors.push('Search query is required');
        }
        break;
    }

    return { errors, warnings };
  }

  protected shouldRequireApproval(request: MCPOperationRequest): boolean {
    // Notion에서는 create, update도 승인 필요
    return ['create', 'update'].includes(request.operation);
  }

  // === Notion API 작업 구현 ===

  private async readPage(pageId: string): Promise<MCPOperationResult> {
    // TODO: 실제 Notion API 호출
    console.log(`[NotionService] Reading page: ${pageId}`);
    return {
      success: true,
      data: {
        id: pageId,
        title: 'Sample Page',
        content: '페이지 내용...',
      },
    };
  }

  private async searchPages(params: { query: string }): Promise<MCPOperationResult> {
    console.log(`[NotionService] Searching pages: ${params.query}`);
    return {
      success: true,
      data: {
        results: [],
        hasMore: false,
      },
    };
  }

  private async listPages(parentPath?: string): Promise<MCPOperationResult> {
    console.log(`[NotionService] Listing pages in: ${parentPath || 'root'}`);
    return {
      success: true,
      data: {
        pages: [],
      },
    };
  }

  private async createPage(
    parentPath: string,
    payload: Record<string, unknown>
  ): Promise<MCPOperationResult> {
    console.log(`[NotionService] Creating page in: ${parentPath}`);
    return {
      success: true,
      data: {
        id: 'new-page-id',
        url: 'https://notion.so/new-page',
        ...payload,
      },
    };
  }

  private async updatePage(
    pageId: string,
    payload: Record<string, unknown>
  ): Promise<MCPOperationResult> {
    console.log(`[NotionService] Updating page: ${pageId}`);
    return {
      success: true,
      data: {
        id: pageId,
        ...payload,
      },
    };
  }

  private async archivePage(pageId: string): Promise<MCPOperationResult> {
    console.log(`[NotionService] Archiving page: ${pageId}`);
    return {
      success: true,
      data: {
        id: pageId,
        archived: true,
      },
    };
  }
}
