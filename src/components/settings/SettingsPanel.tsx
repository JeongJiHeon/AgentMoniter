import { useState } from 'react';
import type { AppSettings, MCPService, LLMConfig, CustomAgentConfig } from '../../types';
import { MCPSettings } from './MCPSettings';
import { LLMSettings } from './LLMSettings';
import { ExternalAPISettings } from './ExternalAPISettings';
import { AgentSettings } from './AgentSettings';

interface SettingsPanelProps {
  settings: AppSettings;
  customAgents: CustomAgentConfig[];
  onUpdateSettings: (updates: Partial<AppSettings>) => void;
  onUpdateAgent: (id: string, updates: Partial<CustomAgentConfig>) => void;
  onDeleteAgent: (id: string) => void;
}

type SettingsTab = 'mcp' | 'llm' | 'api' | 'agents';

export function SettingsPanel({
  settings,
  customAgents,
  onUpdateSettings,
  onUpdateAgent,
  onDeleteAgent,
}: SettingsPanelProps) {
  const [activeTab, setActiveTab] = useState<SettingsTab>('mcp');

  const tabs: Array<{ id: SettingsTab; label: string; count?: number }> = [
    { id: 'mcp', label: 'MCP 서비스', count: settings.mcpServices.filter(s => s.enabled).length },
    { id: 'llm', label: 'LLM 설정' },
    { id: 'api', label: '외부 API', count: settings.externalAPIs.filter(a => a.status === 'active').length },
    { id: 'agents', label: 'Agent 관리', count: customAgents.filter(a => a.isActive).length },
  ];

  // MCP Handlers
  const handleAddMCPService = (service: Omit<MCPService, 'id' | 'status' | 'lastConnected'>) => {
    const newService: MCPService = {
      ...service,
      id: crypto.randomUUID(),
      status: 'disconnected',
    };
    onUpdateSettings({
      mcpServices: [...settings.mcpServices, newService],
    });
  };

  const handleUpdateMCPService = (id: string, updates: Partial<MCPService>) => {
    onUpdateSettings({
      mcpServices: settings.mcpServices.map(s =>
        s.id === id ? { ...s, ...updates } : s
      ),
    });
  };

  const handleRemoveMCPService = (id: string) => {
    onUpdateSettings({
      mcpServices: settings.mcpServices.filter(s => s.id !== id),
    });
  };

  const handleConnectMCPService = (id: string) => {
    // TODO: 실제 연결 로직 - WebSocket을 통해 서버에 요청
    handleUpdateMCPService(id, { status: 'connecting' });

    // 시뮬레이션
    setTimeout(() => {
      handleUpdateMCPService(id, {
        status: 'connected',
        lastConnected: new Date(),
      });
    }, 1000);
  };

  const handleDisconnectMCPService = (id: string) => {
    handleUpdateMCPService(id, { status: 'disconnected' });
  };

  // LLM Handler
  const handleUpdateLLMConfig = (updates: Partial<LLMConfig>) => {
    onUpdateSettings({
      llmConfig: { ...settings.llmConfig, ...updates },
    });
  };

  // API Handler
  const handleRefreshAPI = (id: string) => {
    // TODO: 실제 헬스체크 로직
    console.log('Refreshing API:', id);
  };

  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700 overflow-hidden h-full">
      {/* Header with Tabs */}
      <div className="border-b border-slate-700">
        <div className="px-6 py-4">
          <h2 className="text-xl font-semibold text-white">설정</h2>
        </div>
        <div className="px-6 flex gap-1">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`
                px-4 py-2 text-sm font-medium rounded-t-lg transition-colors
                ${activeTab === tab.id
                  ? 'bg-slate-700 text-white'
                  : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
                }
              `}
            >
              {tab.label}
              {tab.count !== undefined && (
                <span className={`
                  ml-2 px-1.5 py-0.5 rounded text-xs
                  ${activeTab === tab.id ? 'bg-blue-500/20 text-blue-400' : 'bg-slate-600 text-slate-400'}
                `}>
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="p-6 overflow-y-auto max-h-[calc(100vh-250px)]">
        {activeTab === 'mcp' && (
          <MCPSettings
            services={settings.mcpServices}
            onAddService={handleAddMCPService}
            onUpdateService={handleUpdateMCPService}
            onRemoveService={handleRemoveMCPService}
            onConnectService={handleConnectMCPService}
            onDisconnectService={handleDisconnectMCPService}
          />
        )}

        {activeTab === 'llm' && (
          <LLMSettings
            config={settings.llmConfig}
            availableModels={settings.availableLLMs}
            onUpdateConfig={handleUpdateLLMConfig}
          />
        )}

        {activeTab === 'api' && (
          <ExternalAPISettings
            apis={settings.externalAPIs}
            onRefresh={handleRefreshAPI}
          />
        )}

        {activeTab === 'agents' && (
          <AgentSettings
            agents={customAgents}
            availableMCPs={settings.mcpServices}
            onUpdateAgent={onUpdateAgent}
            onDeleteAgent={onDeleteAgent}
          />
        )}
      </div>
    </div>
  );
}
