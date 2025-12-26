import { useState } from 'react';
import { useAgentStore, useTicketStore } from '../stores';
import { useAllAgents } from '../hooks/useAllAgents';
import { AgentPanel } from '../components/agents/AgentPanel';
import { TicketList } from '../components/tickets/TicketList';
import { ApprovalQueue } from '../components/approval/ApprovalQueue';
import { CreateAgentModal } from '../components/agents/CreateAgentModal';
import { KPIDashboard } from '../components/dashboard/KPIDashboard';

export function DashboardPage() {
  const [isCreateAgentModalOpen, setIsCreateAgentModalOpen] = useState(false);
  const { selectedAgent, setSelectedAgent } = useAgentStore();
  const allAgents = useAllAgents();

  return (
    <div>
      {/* KPI Dashboard */}
      <KPIDashboard />

      {/* Main Dashboard */}
      <div className="grid grid-cols-12 gap-6">
      {/* Left Column - Agent Panel */}
      <div className="col-span-3">
        <AgentPanel agents={allAgents} onAgentSelect={setSelectedAgent} />

        {/* Create Agent Button */}
        <button
          onClick={() => setIsCreateAgentModalOpen(true)}
          className="w-full mt-4 px-4 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-xl flex items-center justify-center gap-2 transition-colors"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          새 Agent 생성
        </button>
      </div>

      {/* Center Column - Ticket List */}
      <div className="col-span-5">
        <TicketList
          tickets={selectedAgent ? useTicketStore.getState().tickets.filter((t) => t.agentId === selectedAgent.id) : useTicketStore.getState().tickets}
          onApprove={() => {}}
          onReject={() => {}}
          onSelectOption={() => {}}
        />
      </div>

      {/* Right Column - Approval Queue */}
      <div className="col-span-4">
        <ApprovalQueue
          requests={useTicketStore.getState().approvalQueue}
          onRespond={() => {}}
        />

        {/* Selected Agent Detail */}
        {selectedAgent && (
          <div className="mt-6 bg-slate-800/50 rounded-xl p-4 border border-slate-700">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-white">Agent 상세</h2>
              <button onClick={() => setSelectedAgent(null)} className="text-slate-400 hover:text-white">
                닫기
              </button>
            </div>
            <div className="space-y-3">
              <div>
                <p className="text-xs text-slate-500">이름</p>
                <p className="text-white">{selectedAgent.name}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">유형</p>
                <p className="text-slate-300">{selectedAgent.type}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">현재 모드</p>
                <p className="text-slate-300">{selectedAgent.thinkingMode}</p>
              </div>
              {selectedAgent.currentTask && (
                <div>
                  <p className="text-xs text-slate-500">현재 작업</p>
                  <p className="text-slate-300">{selectedAgent.currentTask}</p>
                </div>
              )}
              {selectedAgent.constraints.length > 0 && (
                <div>
                  <p className="text-xs text-slate-500 mb-2">제약조건</p>
                  <div className="space-y-1">
                    {selectedAgent.constraints.map((c, i) => (
                      <div key={i} className="px-2 py-1 bg-red-500/10 border border-red-500/30 rounded text-sm text-red-400">
                        {c}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Create Agent Modal */}
      <CreateAgentModal
        isOpen={isCreateAgentModalOpen}
        onClose={() => setIsCreateAgentModalOpen(false)}
        onCreateAgent={(config) => {
          const newAgent = {
            ...config,
            id: crypto.randomUUID(),
            createdAt: new Date(),
            updatedAt: new Date(),
          };
          useAgentStore.getState().addCustomAgent(newAgent);
          setIsCreateAgentModalOpen(false);
        }}
        availableMCPs={useSettingsStore.getState().settings.mcpServices}
        llmConfig={useSettingsStore.getState().settings.llmConfig}
      />
    </div>
    </div>
  );
}

// Import for inline usage
import { useSettingsStore } from '../stores';
