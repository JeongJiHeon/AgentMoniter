import { useState } from 'react';
import { useAgentStore, useSettingsStore } from '../stores';
import { Settings, Cpu, Globe, Users, Server, Activity } from 'lucide-react';
import type { MCPService, LLMConfig } from '../types';
import { MCPSettings } from '../components/settings/MCPSettings';
import { LLMSettings } from '../components/settings/LLMSettings';
import { ExternalAPISettings } from '../components/settings/ExternalAPISettings';
import { AgentSettings } from '../components/settings/AgentSettings';

type SettingsTab = 'mcp' | 'llm' | 'api' | 'agents';

export function EnhancedSettingsPage() {
  const { settings, updateSettings } = useSettingsStore();
  const { customAgents, updateCustomAgent, deleteCustomAgent } = useAgentStore();
  const [activeTab, setActiveTab] = useState<SettingsTab>('mcp');

  const tabs: Array<{
    id: SettingsTab;
    label: string;
    icon: React.ComponentType<{ className?: string }>;
    count?: number;
  }> = [
    {
      id: 'mcp',
      label: 'MCP Services',
      icon: Server,
      count: settings.mcpServices.filter(s => s.enabled).length
    },
    {
      id: 'llm',
      label: 'LLM Config',
      icon: Cpu
    },
    {
      id: 'api',
      label: 'External APIs',
      icon: Globe,
      count: settings.externalAPIs.filter(a => a.status === 'active').length
    },
    {
      id: 'agents',
      label: 'Agents',
      icon: Users,
      count: customAgents.filter(a => a.isActive).length
    },
  ];

  // MCP Handlers
  const handleAddMCPService = (service: Omit<MCPService, 'id' | 'status' | 'lastConnected'>) => {
    const newService: MCPService = {
      ...service,
      id: crypto.randomUUID(),
      status: 'disconnected',
    };
    updateSettings({
      mcpServices: [...settings.mcpServices, newService],
    });
  };

  const handleUpdateMCPService = (id: string, updates: Partial<MCPService>) => {
    updateSettings({
      mcpServices: settings.mcpServices.map(s =>
        s.id === id ? { ...s, ...updates } : s
      ),
    });
  };

  const handleRemoveMCPService = (id: string) => {
    updateSettings({
      mcpServices: settings.mcpServices.filter(s => s.id !== id),
    });
  };

  const handleConnectMCPService = (id: string) => {
    handleUpdateMCPService(id, { status: 'connecting' });
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
    updateSettings({
      llmConfig: { ...settings.llmConfig, ...updates },
    });
  };

  // API Handler
  const handleRefreshAPI = (id: string) => {
    console.log('Refreshing API:', id);
  };

  return (
    <div className="h-screen bg-[#0a0e1a] text-gray-100 overflow-hidden font-mono">
      {/* Background grid effect */}
      <div className="fixed inset-0 bg-[linear-gradient(rgba(34,211,238,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(34,211,238,0.03)_1px,transparent_1px)] bg-[size:40px_40px] pointer-events-none" />

      {/* Scanline effect */}
      <div className="fixed inset-0 bg-[linear-gradient(transparent_50%,rgba(0,217,255,0.02)_50%)] bg-[size:100%_4px] pointer-events-none animate-scanline" />

      <div className="relative z-10 h-full flex flex-col overflow-hidden">
        {/* Header */}
        <div className="border-b border-cyan-400/10 bg-gradient-to-r from-[#0d1117]/95 to-[#0a0e1a]/95 backdrop-blur-xl">
          <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-cyan-400/50 to-transparent" />
          <div className="px-6 py-4">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-xl font-bold bg-gradient-to-r from-cyan-400 to-cyan-300 bg-clip-text text-transparent tracking-tight flex items-center gap-2">
                  <Settings className="w-6 h-6 text-cyan-400" />
                  SYSTEM CONFIGURATION
                </h1>
                <p className="text-xs text-gray-500 mt-0.5 tracking-wider">Agent Monitor Settings & Integrations</p>
              </div>

              <div className="flex items-center gap-3">
                {/* Status Indicators */}
                <div className="flex items-center gap-2 px-3 py-1.5 bg-cyan-500/10 border border-cyan-400/20 rounded-lg">
                  <Activity className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
                  <span className="text-xs text-cyan-300 font-medium">ONLINE</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="border-b border-cyan-400/10 bg-[#0d1117]/50">
          <div className="px-6 flex gap-2">
            {tabs.map(tab => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`
                    relative px-4 py-3 text-sm font-medium transition-all
                    ${activeTab === tab.id
                      ? 'text-cyan-300'
                      : 'text-gray-500 hover:text-gray-300'
                    }
                  `}
                >
                  <div className="flex items-center gap-2">
                    <Icon className="w-4 h-4" />
                    <span>{tab.label}</span>
                    {tab.count !== undefined && (
                      <span className={`
                        px-1.5 py-0.5 rounded text-[10px] font-bold tabular-nums
                        ${activeTab === tab.id
                          ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-400/30'
                          : 'bg-gray-700/50 text-gray-500 border border-gray-600/30'
                        }
                      `}>
                        {tab.count}
                      </span>
                    )}
                  </div>
                  {activeTab === tab.id && (
                    <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-cyan-500 to-magenta-500" />
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden">
          <div className="h-full overflow-y-auto p-6">
            {activeTab === 'mcp' && (
              <div className="max-w-5xl mx-auto">
                <div className="bg-gradient-to-br from-[#1a1f2e]/50 to-[#0d1117]/50 border border-cyan-400/10 rounded-xl backdrop-blur-xl overflow-hidden">
                  <div className="px-6 py-4 border-b border-cyan-400/10">
                    <div className="flex items-center gap-2">
                      <Server className="w-5 h-5 text-cyan-400" />
                      <h2 className="text-lg font-bold text-cyan-300">Model Context Protocol Services</h2>
                    </div>
                    <p className="text-xs text-gray-500 mt-1">
                      Configure external tool providers and integrations
                    </p>
                  </div>
                  <div className="p-6">
                    <MCPSettings
                      services={settings.mcpServices}
                      onAddService={handleAddMCPService}
                      onUpdateService={handleUpdateMCPService}
                      onRemoveService={handleRemoveMCPService}
                      onConnectService={handleConnectMCPService}
                      onDisconnectService={handleDisconnectMCPService}
                    />
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'llm' && (
              <div className="max-w-5xl mx-auto">
                <div className="bg-gradient-to-br from-[#1a1f2e]/50 to-[#0d1117]/50 border border-cyan-400/10 rounded-xl backdrop-blur-xl overflow-hidden">
                  <div className="px-6 py-4 border-b border-cyan-400/10">
                    <div className="flex items-center gap-2">
                      <Cpu className="w-5 h-5 text-cyan-400" />
                      <h2 className="text-lg font-bold text-cyan-300">Language Model Configuration</h2>
                    </div>
                    <p className="text-xs text-gray-500 mt-1">
                      Configure LLM provider, model, and inference parameters
                    </p>
                  </div>
                  <div className="p-6">
                    <LLMSettings
                      config={settings.llmConfig}
                      availableModels={settings.availableLLMs}
                      onUpdateConfig={handleUpdateLLMConfig}
                    />
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'api' && (
              <div className="max-w-5xl mx-auto">
                <div className="bg-gradient-to-br from-[#1a1f2e]/50 to-[#0d1117]/50 border border-cyan-400/10 rounded-xl backdrop-blur-xl overflow-hidden">
                  <div className="px-6 py-4 border-b border-cyan-400/10">
                    <div className="flex items-center gap-2">
                      <Globe className="w-5 h-5 text-cyan-400" />
                      <h2 className="text-lg font-bold text-cyan-300">External API Integrations</h2>
                    </div>
                    <p className="text-xs text-gray-500 mt-1">
                      Monitor and manage external API connections
                    </p>
                  </div>
                  <div className="p-6">
                    <ExternalAPISettings
                      apis={settings.externalAPIs}
                      onRefresh={handleRefreshAPI}
                    />
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'agents' && (
              <div className="max-w-5xl mx-auto">
                <div className="bg-gradient-to-br from-[#1a1f2e]/50 to-[#0d1117]/50 border border-cyan-400/10 rounded-xl backdrop-blur-xl overflow-hidden">
                  <div className="px-6 py-4 border-b border-cyan-400/10">
                    <div className="flex items-center gap-2">
                      <Users className="w-5 h-5 text-cyan-400" />
                      <h2 className="text-lg font-bold text-cyan-300">Custom Agent Management</h2>
                    </div>
                    <p className="text-xs text-gray-500 mt-1">
                      Create and configure custom agents with specialized capabilities
                    </p>
                  </div>
                  <div className="p-6">
                    <AgentSettings
                      agents={customAgents}
                      availableMCPs={settings.mcpServices}
                      onUpdateAgent={updateCustomAgent}
                      onDeleteAgent={deleteCustomAgent}
                    />
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Custom styles */}
      <style>{`
        @keyframes scanline {
          0% { transform: translateY(0); }
          100% { transform: translateY(100vh); }
        }
        .animate-scanline {
          animation: scanline 8s linear infinite;
        }

        /* Custom scrollbar */
        ::-webkit-scrollbar {
          width: 6px;
          height: 6px;
        }
        ::-webkit-scrollbar-track {
          background: rgba(17, 24, 39, 0.3);
        }
        ::-webkit-scrollbar-thumb {
          background: rgba(34, 211, 238, 0.3);
          border-radius: 3px;
        }
        ::-webkit-scrollbar-thumb:hover {
          background: rgba(34, 211, 238, 0.5);
        }
      `}</style>
    </div>
  );
}
