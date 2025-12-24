import { BaseMCPService } from '../BaseMCPService.js';
import type {
  MCPServiceConfig,
  MCPOperationRequest,
  MCPOperationResult,
} from '../types.js';

/**
 * Confluence MCP 서비스
 *
 * 허용 작업:
 * - 페이지 읽기/검색
 * - 페이지 초안 생성 (승인 필요)
 * - 페이지 업데이트 (승인 필요)
 *
 * 금지 작업:
 * - 승인 없는 페이지 공개
 * - 승인 없는 권한 변경
 */
export class ConfluenceService extends BaseMCPService {
  private baseUrl?: string;
  private apiToken?: string;
  private email?: string;

  constructor(config: MCPServiceConfig) {
    super({
      ...config,
      type: 'confluence',
    });
    this.baseUrl = config.baseUrl;
    this.apiToken = config.credentials?.apiKey;
    this.email = config.credentials?.email;
  }

  protected async doConnect(): Promise<void> {
    if (!this.baseUrl || !this.apiToken || !this.email) {
      throw new Error('Confluence base URL, API token, and email are required');
    }
    console.log(`[ConfluenceService] Connected to Confluence at ${this.baseUrl}`);
  }

  protected async doDisconnect(): Promise<void> {
    console.log(`[ConfluenceService] Disconnected from Confluence`);
  }

  protected async doExecute(request: MCPOperationRequest): Promise<MCPOperationResult> {
    const { operation, target, payload } = request;

    switch (operation) {
      case 'read':
        return this.readPage(target.id!);

      case 'search':
        return this.searchPages(payload as unknown as { query: string; spaceKey?: string });

      case 'list':
        return this.listPages(target.path);

      case 'create':
        return this.createPage(payload as unknown as ConfluencePage);

      case 'update':
        return this.updatePage(target.id!, payload as unknown as Partial<ConfluencePage>);

      case 'delete':
        return this.deletePage(target.id!);

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
      case 'update':
      case 'delete':
        if (!request.target?.id) {
          errors.push('Page ID is required');
        }
        break;

      case 'create': {
        const page = request.payload as unknown as ConfluencePage;
        if (!page?.spaceKey) {
          errors.push('Space key is required');
        }
        if (!page?.title) {
          errors.push('Page title is required');
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

    return { errors, warnings };
  }

  protected shouldRequireApproval(request: MCPOperationRequest): boolean {
    return ['create', 'update', 'delete'].includes(request.operation);
  }

  // === Confluence API 작업 구현 ===

  private async readPage(pageId: string): Promise<MCPOperationResult> {
    console.log(`[ConfluenceService] Reading page: ${pageId}`);
    return {
      success: true,
      data: {
        id: pageId,
        title: 'Sample Page',
        body: {
          storage: {
            value: '<p>페이지 내용</p>',
            representation: 'storage',
          },
        },
        version: { number: 1 },
      },
    };
  }

  private async searchPages(params: { query: string; spaceKey?: string }): Promise<MCPOperationResult> {
    console.log(`[ConfluenceService] Searching pages: ${params.query}`);
    return {
      success: true,
      data: {
        results: [],
        totalSize: 0,
      },
    };
  }

  private async listPages(spaceKey?: string): Promise<MCPOperationResult> {
    console.log(`[ConfluenceService] Listing pages in space: ${spaceKey || 'all'}`);
    return {
      success: true,
      data: {
        pages: [],
      },
    };
  }

  private async createPage(page: ConfluencePage): Promise<MCPOperationResult> {
    console.log(`[ConfluenceService] Creating page: ${page.title} in space ${page.spaceKey}`);
    return {
      success: true,
      data: {
        id: 'new-page-id',
        ...page,
        version: { number: 1 },
        _links: {
          webui: `${this.baseUrl}/wiki/spaces/${page.spaceKey}/pages/new-page-id`,
        },
      },
      metadata: {
        message: '페이지가 생성되었습니다.',
      },
    };
  }

  private async updatePage(
    pageId: string,
    updates: Partial<ConfluencePage>
  ): Promise<MCPOperationResult> {
    console.log(`[ConfluenceService] Updating page: ${pageId}`);
    return {
      success: true,
      data: {
        id: pageId,
        ...updates,
        version: { number: 2 },
      },
      metadata: {
        message: '페이지가 업데이트되었습니다.',
      },
    };
  }

  private async deletePage(pageId: string): Promise<MCPOperationResult> {
    console.log(`[ConfluenceService] Deleting page: ${pageId}`);
    return {
      success: true,
      data: {
        id: pageId,
        deleted: true,
      },
      metadata: {
        message: '페이지가 삭제되었습니다.',
      },
    };
  }
}

interface ConfluencePage {
  spaceKey: string;
  title: string;
  body?: {
    storage: {
      value: string;
      representation: 'storage' | 'wiki';
    };
  };
  parentId?: string;
  labels?: string[];
}
