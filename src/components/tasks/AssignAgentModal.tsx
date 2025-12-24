import type { Agent } from '../../types';

interface AssignAgentModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAssign: (agentId: string) => void;
  agents: Agent[];
  taskTitle: string;
}

export function AssignAgentModal({
  isOpen,
  onClose,
  onAssign,
  agents,
  taskTitle,
}: AssignAgentModalProps) {
  if (!isOpen) return null;

  const availableAgents = agents.filter(a => a.isActive || !a.currentTask);

  const handleAssign = (agentId: string) => {
    onAssign(agentId);
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-slate-800 rounded-xl border border-slate-700 w-full max-w-md">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700">
          <div>
            <h2 className="text-lg font-semibold text-white">Agent 할당</h2>
            <p className="text-sm text-slate-400 mt-1">{taskTitle}</p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-6">
          {availableAgents.length === 0 ? (
            <div className="text-center py-8 text-slate-500">
              <p>할당 가능한 Agent가 없습니다.</p>
              <p className="text-sm mt-2">Agent를 생성하거나 활성화해주세요.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {availableAgents.map(agent => (
                <button
                  key={agent.id}
                  onClick={() => handleAssign(agent.id)}
                  className="w-full p-4 bg-slate-700 hover:bg-slate-600 rounded-lg border border-slate-600 hover:border-blue-500 transition-all text-left"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-medium text-white">{agent.name}</h3>
                      <p className="text-xs text-slate-400 mt-1">{agent.type}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      {agent.currentTask && (
                        <span className="text-xs text-orange-400">작업 중</span>
                      )}
                      <span className={`w-2 h-2 rounded-full ${agent.isActive ? 'bg-green-500' : 'bg-slate-500'}`} />
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-slate-700">
          <button
            onClick={onClose}
            className="px-4 py-2 text-slate-400 hover:text-white transition-colors"
          >
            취소
          </button>
        </div>
      </div>
    </div>
  );
}

