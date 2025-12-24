import type { Agent } from '../../types';
import { AgentCard } from './AgentCard';

interface AgentPanelProps {
  agents: Agent[];
  onAgentSelect?: (agent: Agent) => void;
}

export function AgentPanel({ agents, onAgentSelect }: AgentPanelProps) {
  const activeAgents = agents.filter(a => a.isActive);
  const idleAgents = agents.filter(a => !a.isActive);

  return (
    <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-white">Agent 상태</h2>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400">
            활성: {activeAgents.length} / 전체: {agents.length}
          </span>
        </div>
      </div>

      {/* Active Agents */}
      {activeAgents.length > 0 && (
        <div className="mb-4">
          <h3 className="text-xs font-medium text-slate-500 uppercase mb-2">
            활성 Agent
          </h3>
          <div className="grid gap-3">
            {activeAgents.map(agent => (
              <AgentCard
                key={agent.id}
                agent={agent}
                onClick={() => onAgentSelect?.(agent)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Idle Agents */}
      {idleAgents.length > 0 && (
        <div>
          <h3 className="text-xs font-medium text-slate-500 uppercase mb-2">
            대기 중
          </h3>
          <div className="grid gap-2">
            {idleAgents.map(agent => (
              <div
                key={agent.id}
                className="flex items-center justify-between p-2 bg-slate-800 rounded-lg"
              >
                <span className="text-sm text-slate-400">{agent.name}</span>
                <span className="text-xs text-slate-600">{agent.type}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {agents.length === 0 && (
        <div className="text-center py-8 text-slate-500">
          등록된 Agent가 없습니다
        </div>
      )}
    </div>
  );
}
