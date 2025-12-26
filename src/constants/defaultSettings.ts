import type { MCPService, LLMModel, AppSettings } from '../types';

// 초기 MCP 서비스 (Notion, Slack, Confluence)
export const DEFAULT_MCP_SERVICES: MCPService[] = [
  {
    id: crypto.randomUUID(),
    type: 'notion',
    name: 'Notion',
    description: 'Notion 워크스페이스와 연동하여 페이지를 관리합니다',
    status: 'disconnected',
    enabled: true,
    config: {},
  },
  {
    id: crypto.randomUUID(),
    type: 'slack',
    name: 'Slack',
    description: 'Slack 워크스페이스와 연동하여 메시지를 관리합니다',
    status: 'disconnected',
    enabled: true,
    config: {},
  },
  {
    id: crypto.randomUUID(),
    type: 'confluence',
    name: 'Confluence',
    description: 'Confluence 페이지와 연동하여 문서를 관리합니다',
    status: 'disconnected',
    enabled: true,
    config: {},
  },
];

// 사용 가능한 LLM 목록
export const DEFAULT_LLM_MODELS: LLMModel[] = [
  {
    id: 'claude-3-5-sonnet',
    provider: 'anthropic',
    name: 'Claude 3.5 Sonnet',
    description: '빠른 속도와 높은 성능의 균형',
    maxTokens: 200000,
    isAvailable: true,
    isDefault: true,
  },
  {
    id: 'claude-3-opus',
    provider: 'anthropic',
    name: 'Claude 3 Opus',
    description: '가장 강력한 추론 능력',
    maxTokens: 200000,
    isAvailable: true,
    isDefault: false,
  },
  {
    id: 'claude-3-haiku',
    provider: 'anthropic',
    name: 'Claude 3 Haiku',
    description: '가장 빠른 응답 속도',
    maxTokens: 200000,
    isAvailable: true,
    isDefault: false,
  },
  {
    id: 'gpt-4o',
    provider: 'openai',
    name: 'GPT-4o',
    description: 'OpenAI의 최신 멀티모달 모델',
    maxTokens: 128000,
    isAvailable: true,
    isDefault: false,
  },
  {
    id: 'gpt-4-turbo',
    provider: 'openai',
    name: 'GPT-4 Turbo',
    description: '향상된 지시 따르기 능력',
    maxTokens: 128000,
    isAvailable: true,
    isDefault: false,
  },
  {
    id: 'gpt-3.5-turbo',
    provider: 'openai',
    name: 'GPT-3.5 Turbo',
    description: '빠르고 경제적인 모델',
    maxTokens: 16385,
    isAvailable: true,
    isDefault: false,
  },
  {
    id: 'gemini-1.5-pro',
    provider: 'google',
    name: 'Gemini 1.5 Pro',
    description: 'Google의 최신 대규모 컨텍스트 모델',
    maxTokens: 1000000,
    isAvailable: false,
    isDefault: false,
  },
];

// 기본 설정
export const DEFAULT_APP_SETTINGS: AppSettings = {
  mcpServices: DEFAULT_MCP_SERVICES,
  llmConfig: {
    provider: 'anthropic',
    model: 'claude-3-5-sonnet',
    temperature: 0.7,
    maxTokens: 4096,
  },
  availableLLMs: DEFAULT_LLM_MODELS,
  externalAPIs: [
    {
      id: 'api-1',
      name: 'Agent Monitor Server',
      type: 'WebSocket',
      baseUrl: 'ws://localhost:8080',
      status: 'inactive',
    },
  ],
};
