import type { Agent } from '../../types';
import { AgentCard } from './AgentCard';

interface AgentPanelProps {
  agents: Agent[];
  onAgentSelect?: (agent: Agent) => void;
}

export function AgentPanel({ agents, onAgentSelect }: AgentPanelProps) {
  // Filter enabled agents (isActive = configuration enabled)
  const enabledAgents = agents.filter(a => a.isActive);
  const disabledAgents = agents.filter(a => !a.isActive);

  // Among enabled agents, split by runtime status
  const runningAgents = enabledAgents.filter(a => a.thinkingMode !== 'idle');
  const idleAgents = enabledAgents.filter(a => a.thinkingMode === 'idle');

  return (
    <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-white">Agent 상태</h2>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400">
            활성: {enabledAgents.length} / 전체: {agents.length}
          </span>
        </div>
      </div>

      {/* Running Agents */}
      {runningAgents.length > 0 && (
        <div className="mb-4">
          <h3 className="text-xs font-medium text-blue-400 uppercase mb-2 flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse"></span>
            실행 중 ({runningAgents.length})
          </h3>
          <div className="grid gap-3">
            {runningAgents.map(agent => (
              <AgentCard
                key={agent.id}
                agent={agent}
                onClick={() => onAgentSelect?.(agent)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Idle Agents (enabled but not running) */}
      {idleAgents.length > 0 && (
        <div className="mb-4">
          <h3 className="text-xs font-medium text-green-400 uppercase mb-2 flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-green-400"></span>
            활성 Agent ({idleAgents.length})
          </h3>
          <div className="grid gap-3">
            {idleAgents.map(agent => (
              <AgentCard
                key={agent.id}
                agent={agent}
                onClick={() => onAgentSelect?.(agent)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Disabled Agents */}
      {disabledAgents.length > 0 && (
        <div>
          <h3 className="text-xs font-medium text-slate-500 uppercase mb-2">
            비활성 ({disabledAgents.length})
          </h3>
          <div className="grid gap-2">
            {disabledAgents.map(agent => (
              <div
                key={agent.id}
                className="flex items-center justify-between p-2 bg-slate-800 rounded-lg opacity-50"
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
