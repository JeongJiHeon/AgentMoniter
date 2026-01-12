import { useState, useMemo } from 'react';
import { useOutletContext } from 'react-router-dom';
import { useTaskStore, useTicketStore } from '../stores';
import { useAllAgents } from '../hooks/useAllAgents';
import { Activity, Users, Zap, Clock, CheckCircle2, AlertCircle, TrendingUp, Plus, Network } from 'lucide-react';
import type { Agent } from '../types';

interface OutletContext {
  handleApprove: (ticketId: string) => void;
  handleReject: (ticketId: string, reason?: string) => void;
  handleSelectOption: (ticketId: string, optionId: string) => void;
  handleApprovalRespond: (requestId: string, approved: boolean, comment?: string) => void;
  handleCreateAgent: (name: string, description: string, type: string, capabilities: string[]) => void;
  handleAssignAgent: (taskId: string, agentId: string) => void;
  handleRespondInteraction: (interactionId: string, response: string) => void;
  handleSendTaskMessage: (taskId: string, message: string) => void;
  showCreateTaskModal: boolean;
  setShowCreateTaskModal: (show: boolean) => void;
  showCreateAgentModal: boolean;
  setShowCreateAgentModal: (show: boolean) => void;
}

export function EnhancedDashboardPage() {
  const allAgents = useAllAgents();
  const tasks = useTaskStore((state) => state.tasks);
  const { tickets, approvalQueue } = useTicketStore();
  const { setShowCreateAgentModal } = useOutletContext<OutletContext>();

  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);

  // KPI calculations
  const kpis = useMemo(() => {
    const activeAgents = allAgents.filter((a) => a.isActive).length;
    const totalAgents = allAgents.length;

    const pendingTasks = tasks.filter((t) => t.status === 'pending').length;
    const inProgressTasks = tasks.filter((t) => t.status === 'in_progress').length;
    const completedTasks = tasks.filter((t) => t.status === 'completed').length;
    const totalTasks = tasks.length;

    const pendingApprovals = approvalQueue.length;

    const completionRate = totalTasks > 0 ? ((completedTasks / totalTasks) * 100).toFixed(1) : '0';

    return {
      activeAgents,
      totalAgents,
      pendingTasks,
      inProgressTasks,
      completedTasks,
      totalTasks,
      pendingApprovals,
      completionRate,
    };
  }, [allAgents, tasks, approvalQueue]);

  // Group agents
  const { runningAgents, idleAgents, disabledAgents } = useMemo(() => {
    const enabled = allAgents.filter(a => a.isActive);
    const disabled = allAgents.filter(a => !a.isActive);
    const running = enabled.filter(a => a.thinkingMode !== 'idle');
    const idle = enabled.filter(a => a.thinkingMode === 'idle');

    return { runningAgents: running, idleAgents: idle, disabledAgents: disabled };
  }, [allAgents]);

  const selectedAgentData = allAgents.find(a => a.id === selectedAgentId);

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
            <div>
              <h1 className="text-xl font-bold bg-gradient-to-r from-cyan-400 to-cyan-300 bg-clip-text text-transparent tracking-tight">
                SYSTEM DASHBOARD
              </h1>
              <p className="text-xs text-gray-500 mt-0.5 tracking-wider">AGENT MONITOR v2.0</p>
            </div>
          </div>
        </div>

        {/* KPI Stats */}
        <div className="px-6 py-4">
          <div className="grid grid-cols-4 gap-4">
            {/* Active Agents KPI */}
            <div className="bg-gradient-to-br from-[#1a1f2e]/50 to-[#0d1117]/50 border border-cyan-400/10 rounded-xl p-4 backdrop-blur-xl hover:border-cyan-400/30 transition-all">
              <div className="flex items-center justify-between mb-3">
                <div className="p-2 bg-cyan-500/10 border border-cyan-400/20 rounded-lg">
                  <Users className="w-5 h-5 text-cyan-400" />
                </div>
                <TrendingUp className="w-4 h-4 text-emerald-400" />
              </div>
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Active Agents</p>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-bold text-cyan-300 tabular-nums">{kpis.activeAgents}</span>
                <span className="text-sm text-gray-500 font-mono">/ {kpis.totalAgents}</span>
              </div>
            </div>

            {/* In Progress Tasks KPI */}
            <div className="bg-gradient-to-br from-[#1a1f2e]/50 to-[#0d1117]/50 border border-cyan-400/10 rounded-xl p-4 backdrop-blur-xl hover:border-cyan-400/30 transition-all">
              <div className="flex items-center justify-between mb-3">
                <div className="p-2 bg-green-500/10 border border-green-400/20 rounded-lg">
                  <Activity className="w-5 h-5 text-green-400 animate-pulse" />
                </div>
              </div>
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">In Progress</p>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-bold text-green-300 tabular-nums">{kpis.inProgressTasks}</span>
                <span className="text-sm text-gray-500 font-mono">/ {kpis.totalTasks}</span>
              </div>
            </div>

            {/* Completion Rate KPI */}
            <div className="bg-gradient-to-br from-[#1a1f2e]/50 to-[#0d1117]/50 border border-cyan-400/10 rounded-xl p-4 backdrop-blur-xl hover:border-cyan-400/30 transition-all">
              <div className="flex items-center justify-between mb-3">
                <div className="p-2 bg-magenta-500/10 border border-magenta-400/20 rounded-lg">
                  <Zap className="w-5 h-5 text-magenta-400" />
                </div>
              </div>
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Completion</p>
              <div className="flex items-baseline gap-2 mb-2">
                <span className="text-3xl font-bold text-magenta-300 tabular-nums">{kpis.completionRate}%</span>
              </div>
              <div className="h-1 bg-gray-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-magenta-500 to-magenta-400 transition-all duration-700"
                  style={{ width: `${kpis.completionRate}%` }}
                />
              </div>
            </div>

            {/* Pending Approvals KPI */}
            <div className="bg-gradient-to-br from-[#1a1f2e]/50 to-[#0d1117]/50 border border-cyan-400/10 rounded-xl p-4 backdrop-blur-xl hover:border-cyan-400/30 transition-all">
              <div className="flex items-center justify-between mb-3">
                <div className="p-2 bg-amber-500/10 border border-amber-400/20 rounded-lg">
                  <Clock className="w-5 h-5 text-amber-400" />
                </div>
                {kpis.pendingApprovals > 0 && (
                  <div className="flex items-center gap-1 text-xs text-amber-400">
                    <div className="w-2 h-2 bg-amber-400 rounded-full animate-pulse" />
                  </div>
                )}
              </div>
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Pending</p>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-bold text-amber-300 tabular-nums">{kpis.pendingApprovals}</span>
                <span className="text-sm text-gray-500 font-mono">approvals</span>
              </div>
            </div>
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="flex-1 grid grid-cols-12 gap-4 px-6 pb-6 overflow-hidden">
          {/* Left Panel - Agents */}
          <div className="col-span-3 flex flex-col gap-4 overflow-hidden">
            <div className="flex-1 bg-gradient-to-br from-[#1a1f2e]/50 to-[#0d1117]/50 border border-cyan-400/10 rounded-xl backdrop-blur-xl overflow-hidden flex flex-col">
              <div className="px-4 py-3 border-b border-cyan-400/10">
                <h2 className="text-sm font-bold text-cyan-300 tracking-wider uppercase flex items-center gap-2">
                  <Network className="w-4 h-4" />
                  Agents ({allAgents.length})
                </h2>
              </div>

              <div className="flex-1 overflow-y-auto p-3 space-y-3">
                {/* Running Agents */}
                {runningAgents.length > 0 && (
                  <div>
                    <div className="flex items-center gap-2 px-2 py-1 mb-2">
                      <Activity className="w-3 h-3 text-green-400 animate-pulse" />
                      <span className="text-xs font-medium text-gray-400 uppercase">Running ({runningAgents.length})</span>
                    </div>
                    <div className="space-y-2">
                      {runningAgents.map(agent => (
                        <AgentCard
                          key={agent.id}
                          agent={agent}
                          isSelected={selectedAgentId === agent.id}
                          onClick={() => setSelectedAgentId(agent.id)}
                        />
                      ))}
                    </div>
                  </div>
                )}

                {/* Idle Agents */}
                {idleAgents.length > 0 && (
                  <div>
                    <div className="flex items-center gap-2 px-2 py-1 mb-2">
                      <CheckCircle2 className="w-3 h-3 text-cyan-400" />
                      <span className="text-xs font-medium text-gray-400 uppercase">Active ({idleAgents.length})</span>
                    </div>
                    <div className="space-y-2">
                      {idleAgents.map(agent => (
                        <AgentCard
                          key={agent.id}
                          agent={agent}
                          isSelected={selectedAgentId === agent.id}
                          onClick={() => setSelectedAgentId(agent.id)}
                        />
                      ))}
                    </div>
                  </div>
                )}

                {/* Disabled Agents */}
                {disabledAgents.length > 0 && (
                  <div>
                    <div className="flex items-center gap-2 px-2 py-1 mb-2">
                      <span className="text-xs font-medium text-gray-600 uppercase">Disabled ({disabledAgents.length})</span>
                    </div>
                    <div className="space-y-2">
                      {disabledAgents.map(agent => (
                        <div
                          key={agent.id}
                          className="px-3 py-2 bg-gray-800/30 rounded-lg border border-gray-700/30 opacity-50"
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-xs text-gray-500">{agent.name}</span>
                            <span className="text-[10px] text-gray-600 uppercase">{agent.type}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {allAgents.length === 0 && (
                  <div className="flex flex-col items-center justify-center h-full text-gray-600">
                    <Network className="w-12 h-12 mb-3 opacity-20" />
                    <p className="text-sm">No agents</p>
                  </div>
                )}
              </div>
            </div>

            {/* Create Agent Button */}
            <button
              onClick={() => setShowCreateAgentModal(true)}
              className="flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-cyan-500 to-cyan-600 hover:from-cyan-400 hover:to-cyan-500 text-white rounded-lg text-sm font-medium transition-all shadow-lg shadow-cyan-500/20 hover:shadow-cyan-500/40 border border-cyan-400/50"
            >
              <Plus className="w-4 h-4" />
              New Agent
            </button>
          </div>

          {/* Center Panel - Activity/Tickets */}
          <div className="col-span-6 bg-gradient-to-br from-[#1a1f2e]/50 to-[#0d1117]/50 border border-cyan-400/10 rounded-xl backdrop-blur-xl overflow-hidden flex flex-col">
            <div className="px-4 py-3 border-b border-cyan-400/10">
              <h2 className="text-sm font-bold text-cyan-300 tracking-wider uppercase">System Activity</h2>
            </div>

            <div className="flex-1 overflow-y-auto p-4">
              {tickets.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-gray-600">
                  <Activity className="w-16 h-16 mb-4 opacity-20" />
                  <p className="text-sm">No activity</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {tickets.slice(0, 20).map(ticket => (
                    <div
                      key={ticket.id}
                      className="p-3 bg-gradient-to-br from-gray-800/30 to-gray-900/30 border border-gray-700/30 rounded-lg hover:border-cyan-400/30 transition-colors"
                    >
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <span className="text-sm text-gray-300 flex-1 line-clamp-2">{ticket.purpose}</span>
                        <StatusBadge status={ticket.status} />
                      </div>
                      <div className="flex items-center justify-between text-xs text-gray-500">
                        <span>Priority: {ticket.priority}</span>
                        <time>{new Date(ticket.createdAt).toLocaleTimeString()}</time>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Right Panel - Approvals & Details */}
          <div className="col-span-3 flex flex-col gap-4 overflow-hidden">
            {/* Approval Queue */}
            <div className="flex-1 bg-gradient-to-br from-[#1a1f2e]/50 to-[#0d1117]/50 border border-cyan-400/10 rounded-xl backdrop-blur-xl overflow-hidden flex flex-col">
              <div className="px-4 py-3 border-b border-cyan-400/10">
                <h2 className="text-sm font-bold text-amber-300 tracking-wider uppercase flex items-center gap-2">
                  <AlertCircle className="w-4 h-4" />
                  Approvals ({approvalQueue.length})
                </h2>
              </div>

              <div className="flex-1 overflow-y-auto p-3">
                {approvalQueue.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full text-gray-600">
                    <CheckCircle2 className="w-12 h-12 mb-3 opacity-20" />
                    <p className="text-xs">All clear</p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {approvalQueue.map(request => (
                      <div
                        key={request.id}
                        className="p-3 bg-amber-500/10 border border-amber-400/30 rounded-lg"
                      >
                        <div className="text-xs text-amber-300 font-medium mb-2 uppercase">{request.type}</div>
                        <p className="text-xs text-gray-300 mb-3 line-clamp-3">{request.message}</p>
                        <div className="flex gap-2">
                          <button className="flex-1 px-2 py-1 bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-400/30 rounded text-xs text-emerald-300 transition-colors">
                            Approve
                          </button>
                          <button className="flex-1 px-2 py-1 bg-red-500/20 hover:bg-red-500/30 border border-red-400/30 rounded text-xs text-red-300 transition-colors">
                            Reject
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Selected Agent Detail */}
            {selectedAgentData && (
              <div className="bg-gradient-to-br from-[#1a1f2e]/50 to-[#0d1117]/50 border border-cyan-400/10 rounded-xl backdrop-blur-xl p-4">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-bold text-cyan-300 uppercase">Agent Detail</h3>
                  <button
                    onClick={() => setSelectedAgentId(null)}
                    className="text-gray-500 hover:text-gray-300 text-xs"
                  >
                    Close
                  </button>
                </div>
                <div className="space-y-3">
                  <div>
                    <p className="text-[10px] text-gray-500 uppercase">Name</p>
                    <p className="text-sm text-white">{selectedAgentData.name}</p>
                  </div>
                  <div>
                    <p className="text-[10px] text-gray-500 uppercase">Type</p>
                    <p className="text-xs text-gray-300">{selectedAgentData.type}</p>
                  </div>
                  <div>
                    <p className="text-[10px] text-gray-500 uppercase">Mode</p>
                    <p className="text-xs text-gray-300">{selectedAgentData.thinkingMode}</p>
                  </div>
                  {selectedAgentData.currentTask && (
                    <div>
                      <p className="text-[10px] text-gray-500 uppercase">Current Task</p>
                      <p className="text-xs text-cyan-300">{selectedAgentData.currentTask}</p>
                    </div>
                  )}
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

interface AgentCardProps {
  agent: Agent;
  isSelected: boolean;
  onClick: () => void;
}

function AgentCard({ agent, isSelected, onClick }: AgentCardProps) {
  const isRunning = agent.thinkingMode !== 'idle';

  return (
    <button
      onClick={onClick}
      className={`
        w-full text-left p-3 rounded-lg border transition-all duration-200
        ${isSelected
          ? 'border-cyan-400 shadow-lg shadow-cyan-500/30 bg-gradient-to-br from-cyan-500/10 to-magenta-500/5'
          : isRunning
          ? 'border-green-400/30 bg-green-500/5 hover:border-green-400/50'
          : 'border-gray-700/30 bg-gray-800/20 hover:border-cyan-400/50'
        }
      `}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-200">{agent.name}</span>
        {isRunning && <Activity className="w-3 h-3 text-green-400 animate-pulse" />}
      </div>
      <div className="flex items-center justify-between text-[10px] text-gray-500">
        <span className="uppercase">{agent.type}</span>
        <span className="uppercase">{agent.thinkingMode}</span>
      </div>
    </button>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors = {
    pending: 'bg-amber-500/20 text-amber-300 border-amber-400/30',
    in_progress: 'bg-cyan-500/20 text-cyan-300 border-cyan-400/30',
    completed: 'bg-emerald-500/20 text-emerald-300 border-emerald-400/30',
    failed: 'bg-red-500/20 text-red-300 border-red-400/30',
  };

  return (
    <span className={`px-2 py-0.5 rounded text-[10px] font-medium uppercase border ${colors[status as keyof typeof colors] || colors.pending}`}>
      {status}
    </span>
  );
}
