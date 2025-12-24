import type { Agent } from '../../types';

interface OrchestrationViewProps {
  orchestrator?: Agent;
  subAgents: Agent[];
}

export function OrchestrationView({ orchestrator, subAgents }: OrchestrationViewProps) {
  if (!orchestrator || orchestrator.role !== 'orchestration') {
    return null;
  }

  const activeSubAgents = subAgents.filter(a => a.isActive);
  const idleSubAgents = subAgents.filter(a => !a.isActive);

  return (
    <div className="p-4 bg-slate-700/50 rounded-lg border border-slate-600">
      <h3 className="text-sm font-medium text-white mb-4 flex items-center gap-2">
        <span className="text-lg">🎭</span>
        Multi-Agent Collaboration
      </h3>

      {/* Orchestrator */}
      <div className="mb-4">
        <div className="flex items-center gap-3 p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg">
          <div className="w-10 h-10 bg-blue-500 rounded-lg flex items-center justify-center text-white font-bold">
            O
          </div>
          <div className="flex-1">
            <p className="text-sm font-medium text-white">{orchestrator.name}</p>
            <p className="text-xs text-slate-400">Orchestration Agent</p>
          </div>
          <div className="text-xs text-blue-400">
            {orchestrator.thinkingMode === 'idle' ? '⏸ Idle' :
             orchestrator.thinkingMode === 'exploring' ? '🔍 Exploring' :
             orchestrator.thinkingMode === 'structuring' ? '🏗️ Structuring' :
             orchestrator.thinkingMode === 'validating' ? '✅ Validating' :
             '📝 Summarizing'}
          </div>
        </div>
      </div>

      {/* Sub Agents */}
      {subAgents.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <div className="flex-1 border-t border-slate-600"></div>
            <span className="text-xs text-slate-400">Coordinates</span>
            <div className="flex-1 border-t border-slate-600"></div>
          </div>

          <div className="space-y-2">
            {/* Active Sub Agents */}
            {activeSubAgents.map(agent => (
              <div
                key={agent.id}
                className="flex items-center gap-3 p-3 bg-green-500/10 border border-green-500/30 rounded-lg"
              >
                <div className="w-8 h-8 bg-green-500 rounded-lg flex items-center justify-center text-white text-xs font-bold">
                  S
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-white">{agent.name}</p>
                  <p className="text-xs text-slate-400">{agent.type}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                  <span className="text-xs text-green-400">Active</span>
                </div>
              </div>
            ))}

            {/* Idle Sub Agents */}
            {idleSubAgents.map(agent => (
              <div
                key={agent.id}
                className="flex items-center gap-3 p-3 bg-slate-800/50 border border-slate-600 rounded-lg opacity-60"
              >
                <div className="w-8 h-8 bg-slate-600 rounded-lg flex items-center justify-center text-white text-xs font-bold">
                  S
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-white">{agent.name}</p>
                  <p className="text-xs text-slate-400">{agent.type}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 bg-slate-500 rounded-full"></span>
                  <span className="text-xs text-slate-400">Idle</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {subAgents.length === 0 && (
        <div className="text-center py-8 text-slate-500">
          <p className="text-sm">No sub-agents assigned yet</p>
          <p className="text-xs mt-1">Orchestrator will assign specialists as needed</p>
        </div>
      )}
    </div>
  );
}
