import React from 'react';
import type { Task, TaskStatus, TaskPriority } from '../../types/task';
import type { Agent, TaskChatMessage } from '../../types';
import { getStatusColor, getStatusLabel, getStatusIcon } from '../../types/agentResult';
import { AssignAgentModal } from './AssignAgentModal';
import { TaskChatDrawer } from './TaskChatDrawer';

interface TaskCardProps {
  task: Task;
  agents: Agent[];
  onStatusChange: (id: string, status: TaskStatus) => void;
  onUpdate: (id: string, updates: Partial<Task>) => void;
  onDelete: (id: string) => void;
  onAssignAgent?: (taskId: string, agentId: string) => void;
  onViewDetail?: (taskId: string) => void;
  autoAssignMode?: 'global' | 'manual';
  taskChatMessages?: TaskChatMessage[];
  onSendTaskMessage?: (taskId: string, message: string) => void;
}

const priorityColors: Record<TaskPriority, string> = {
  low: 'bg-slate-600 text-slate-300',
  medium: 'bg-blue-600 text-blue-100',
  high: 'bg-orange-600 text-orange-100',
  urgent: 'bg-red-600 text-red-100',
};

const statusColors: Record<TaskStatus, string> = {
  pending: 'border-slate-600',
  in_progress: 'border-blue-500',
  completed: 'border-green-500 opacity-60',
  cancelled: 'border-red-500 opacity-50',
};

// 상태에 따른 행동 유도 메시지
const getActionMessage = (task: Task, assignedAgent?: Agent, allAgents?: Agent[]): string => {
  if (task.status === 'completed') return 'Completed';
  if (task.status === 'cancelled') return 'Cancelled';
  if (!task.assignedAgentId) return 'No agent assigned';
  if (task.status === 'pending') return 'Waiting to start';
  if (task.status === 'in_progress') {
    if (assignedAgent?.thinkingMode === 'idle') return 'Agent idle';

    // Orchestration Agent인 경우 sub agent 개수 표시
    if (assignedAgent?.role === 'orchestration' && assignedAgent.subAgents && assignedAgent.subAgents.length > 0) {
      const activeSubAgents = assignedAgent.subAgents.filter(subId =>
        allAgents?.find(a => a.id === subId && a.isActive)
      ).length;
      return `Running with ${activeSubAgents} agent${activeSubAgents !== 1 ? 's' : ''}`;
    }

    return 'Running';
  }
  return 'Unknown status';
};

export function TaskCard({ task, agents, onStatusChange, onUpdate, onDelete, onAssignAgent, onViewDetail, autoAssignMode = 'manual', taskChatMessages = [], onSendTaskMessage }: TaskCardProps) {
  const [showAssignModal, setShowAssignModal] = React.useState(false);
  const [showChatDrawer, setShowChatDrawer] = React.useState(false);
  const [userResponse, setUserResponse] = React.useState('');

  const assignedAgent = agents.find(a => a.id === task.assignedAgentId);
  const actionMessage = getActionMessage(task, assignedAgent, agents);

  // Filter chat messages for this task
  const taskMessages = taskChatMessages.filter(msg => msg.taskId === task.id);

  const handleAssign = (agentId: string) => {
    if (onAssignAgent) {
      onAssignAgent(task.id, agentId);
      onUpdate(task.id, { assignedAgentId: agentId, status: 'in_progress' });
    }
  };

  const handleUserResponse = () => {
    if (userResponse.trim() && onSendTaskMessage) {
      onSendTaskMessage(task.id, userResponse.trim());
      setUserResponse('');
    }
  };

  return (
    <div
      className={`p-3 bg-slate-700 rounded-lg border ${statusColors[task.status]} transition-all hover:border-slate-500`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h4 className="text-sm font-medium text-white truncate">{task.title}</h4>
            <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${priorityColors[task.priority]}`}>
              {task.priority === 'urgent' ? '긴급' : task.priority === 'high' ? '높음' : task.priority === 'medium' ? '보통' : '낮음'}
            </span>
          </div>
          {task.description && (
            <p className="text-xs text-slate-400 line-clamp-2 mb-2">{task.description}</p>
          )}
          <div className="flex items-center gap-2 flex-wrap mb-2">
            {task.tags.length > 0 && (
              <div className="flex gap-1 flex-wrap">
                {task.tags.slice(0, 2).map((tag, idx) => (
                  <span key={idx} className="px-1.5 py-0.5 bg-slate-600 text-slate-300 text-xs rounded">
                    {tag}
                  </span>
                ))}
                {task.tags.length > 2 && (
                  <span className="text-xs text-slate-500">+{task.tags.length - 2}</span>
                )}
              </div>
            )}
            {task.source !== 'manual' && (
              <span className="text-xs text-slate-500">
                {task.source === 'slack' ? '💬 Slack' : task.source === 'confluence' ? '📄 Confluence' : task.source}
              </span>
            )}
          </div>

          {/* Action Message */}
          <div className={`text-xs font-medium mb-3 ${
            !task.assignedAgentId ? 'text-yellow-400' :
            task.status === 'completed' ? 'text-green-400' :
            task.status === 'in_progress' ? 'text-blue-400' :
            'text-slate-400'
          }`}>
            Status: {actionMessage}
            {assignedAgent && task.status === 'in_progress' && (
              <span className="ml-2 text-slate-400">({assignedAgent.name})</span>
            )}
          </div>

          {/* Agent Lifecycle Status Badge */}
          {task.agentLifecycleStatus && (
            <div className="mb-3">
              <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold ${getStatusColor(task.agentLifecycleStatus)}`}>
                <span>{getStatusIcon(task.agentLifecycleStatus)}</span>
                <span>{getStatusLabel(task.agentLifecycleStatus)}</span>
              </span>
            </div>
          )}

          {/* Pending Question */}
          {task.pendingQuestion && task.agentLifecycleStatus === 'WAITING_USER' && (
            <div className="mb-3 p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <svg className="w-4 h-4 text-amber-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <p className="text-xs font-semibold text-amber-400">Agent Question</p>
              </div>
              <p className="text-xs text-white mb-2 leading-relaxed">{task.pendingQuestion}</p>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={userResponse}
                  onChange={(e) => setUserResponse(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                      handleUserResponse();
                    }
                  }}
                  placeholder="Type your answer..."
                  className="flex-1 px-2 py-1.5 bg-slate-800 border border-slate-600 rounded text-white text-xs placeholder-slate-500 focus:outline-none focus:border-amber-500"
                />
                <button
                  onClick={handleUserResponse}
                  disabled={!userResponse.trim()}
                  className="px-3 py-1.5 bg-amber-600 hover:bg-amber-500 disabled:bg-slate-600 disabled:cursor-not-allowed text-white text-xs font-medium rounded transition-colors"
                >
                  Send
                </button>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex items-center gap-2">
            {onSendTaskMessage && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setShowChatDrawer(true);
                }}
                className="px-3 py-1.5 bg-slate-600 hover:bg-slate-500 text-white text-xs font-medium rounded transition-colors flex items-center gap-1"
                title="Chat with agent about this task"
              >
                💬 Chat
                {taskMessages.length > 0 && (
                  <span className="ml-1 px-1.5 py-0.5 bg-blue-500 text-white text-xs rounded-full">
                    {taskMessages.length}
                  </span>
                )}
              </button>
            )}
            {onViewDetail && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onViewDetail(task.id);
                }}
                className="px-3 py-1.5 bg-slate-600 hover:bg-slate-500 text-white text-xs font-medium rounded transition-colors"
              >
                View Detail
              </button>
            )}
            {!task.assignedAgentId && onAssignAgent && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setShowAssignModal(true);
                }}
                className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium rounded transition-colors"
              >
                Assign Agent
              </button>
            )}
            {task.status !== 'completed' && task.status !== 'cancelled' && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onStatusChange(task.id, 'cancelled');
                }}
                className="px-3 py-1.5 bg-slate-700 hover:bg-red-600 text-slate-300 hover:text-white text-xs font-medium rounded transition-colors"
              >
                Cancel
              </button>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1">
          {/* 자동 할당 토글 (수동 모드일 때만 표시) */}
          {autoAssignMode === 'manual' && task.autoAssign !== undefined && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onUpdate(task.id, { autoAssign: !task.autoAssign });
              }}
              className={`p-1 rounded transition-colors ${
                task.autoAssign
                  ? 'text-green-400 hover:text-green-300 bg-green-500/20'
                  : 'text-slate-400 hover:text-slate-300'
              }`}
              title={task.autoAssign ? '자동 할당 끄기' : '자동 할당 켜기'}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                {task.autoAssign ? (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 9v6m4-6v6m7 3H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v10a2 2 0 01-2 2z" />
                )}
              </svg>
            </button>
          )}
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete(task.id);
            }}
            className="p-1 text-slate-400 hover:text-red-400 transition-colors"
            title="삭제"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
      <div className="mt-2 flex items-center justify-between text-xs text-slate-500">
        <span>{new Date(task.createdAt).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' })}</span>
      </div>

      <AssignAgentModal
        isOpen={showAssignModal}
        onClose={() => setShowAssignModal(false)}
        onAssign={handleAssign}
        agents={agents}
        taskTitle={task.title}
      />

      {onSendTaskMessage && (
        <TaskChatDrawer
          isOpen={showChatDrawer}
          onClose={() => setShowChatDrawer(false)}
          task={task}
          messages={taskMessages}
          onSendMessage={onSendTaskMessage}
        />
      )}
    </div>
  );
}

