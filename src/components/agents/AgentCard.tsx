import type { Agent, ThinkingMode } from '../../types';

interface AgentCardProps {
  agent: Agent;
  onClick?: () => void;
}

const thinkingModeConfig: Record<ThinkingMode, { label: string; color: string; bgColor: string }> = {
  idle: { label: '대기', color: 'text-gray-400', bgColor: 'bg-gray-500/20' },
  exploring: { label: '탐색', color: 'text-blue-400', bgColor: 'bg-blue-500/20' },
  structuring: { label: '구조화', color: 'text-purple-400', bgColor: 'bg-purple-500/20' },
  validating: { label: '검증', color: 'text-amber-400', bgColor: 'bg-amber-500/20' },
  summarizing: { label: '요약', color: 'text-emerald-400', bgColor: 'bg-emerald-500/20' },
};

export function AgentCard({ agent, onClick }: AgentCardProps) {
  const modeConfig = thinkingModeConfig[agent.thinkingMode];

  return (
    <div
      onClick={onClick}
      className={`
        bg-slate-800 rounded-lg p-4 border border-slate-700
        hover:border-slate-600 transition-all cursor-pointer
        ${agent.isActive ? 'ring-2 ring-blue-500/50' : ''}
      `}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="font-medium text-white">{agent.name}</h3>
          <p className="text-xs text-slate-500">{agent.type}</p>
        </div>
        <div className={`px-2 py-1 rounded-full text-xs ${modeConfig.bgColor} ${modeConfig.color}`}>
          {modeConfig.label}
        </div>
      </div>

      {/* Current Task */}
      {agent.currentTask && (
        <div className="mb-3">
          <p className="text-xs text-slate-500 mb-1">현재 작업</p>
          <p className="text-sm text-slate-300 line-clamp-2">{agent.currentTask}</p>
        </div>
      )}

      {/* Active Constraints */}
      {agent.constraints.length > 0 && (
        <div className="mb-3">
          <p className="text-xs text-slate-500 mb-1">활성 제약조건</p>
          <div className="flex flex-wrap gap-1">
            {agent.constraints.slice(0, 3).map((constraint, idx) => (
              <span
                key={idx}
                className="px-2 py-0.5 bg-slate-700 rounded text-xs text-slate-400"
              >
                {constraint}
              </span>
            ))}
            {agent.constraints.length > 3 && (
              <span className="text-xs text-slate-500">
                +{agent.constraints.length - 3}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between text-xs text-slate-500">
        <span>
          마지막 활동: {formatRelativeTime(agent.lastActivity)}
        </span>
        <div className={`w-2 h-2 rounded-full ${agent.isActive ? 'bg-green-500' : 'bg-slate-600'}`} />
      </div>
    </div>
  );
}

function formatRelativeTime(date: Date): string {
  const now = new Date();
  const diff = now.getTime() - new Date(date).getTime();
  const minutes = Math.floor(diff / 60000);

  if (minutes < 1) return '방금 전';
  if (minutes < 60) return `${minutes}분 전`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}시간 전`;
  return `${Math.floor(hours / 24)}일 전`;
}
