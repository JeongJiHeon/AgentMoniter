import React from 'react';
import type { Task, TaskStatus, TaskPriority } from '../../types/task';
import type { Agent } from '../../types';
import { AssignAgentModal } from './AssignAgentModal';

interface TaskCardProps {
  task: Task;
  agents: Agent[];
  onStatusChange: (id: string, status: TaskStatus) => void;
  onUpdate: (id: string, updates: Partial<Task>) => void;
  onDelete: (id: string) => void;
  onAssignAgent?: (taskId: string, agentId: string) => void;
  onViewDetail?: (taskId: string) => void;
  autoAssignMode?: 'global' | 'manual';
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

export function TaskCard({ task, agents, onStatusChange, onUpdate, onDelete, onAssignAgent, onViewDetail, autoAssignMode = 'manual' }: TaskCardProps) {
  const [showAssignModal, setShowAssignModal] = React.useState(false);
  
  const handleStatusClick = () => {
    const statusOrder: TaskStatus[] = ['pending', 'in_progress', 'completed'];
    const currentIndex = statusOrder.indexOf(task.status);
    const nextIndex = (currentIndex + 1) % statusOrder.length;
    onStatusChange(task.id, statusOrder[nextIndex]);
  };

  const assignedAgent = agents.find(a => a.id === task.assignedAgentId);

  const handleAssign = (agentId: string) => {
    if (onAssignAgent) {
      onAssignAgent(task.id, agentId);
      onUpdate(task.id, { assignedAgentId: agentId, status: 'in_progress' });
    }
  };

  return (
    <div
      className={`p-3 bg-slate-700 rounded-lg border ${statusColors[task.status]} cursor-pointer hover:bg-slate-650 transition-all`}
      onClick={handleStatusClick}
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
          <div className="flex items-center gap-2 flex-wrap">
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
            {assignedAgent && (
              <span className="text-xs text-blue-400">
                🤖 {assignedAgent.name}
              </span>
            )}
            {task.autoAssign !== undefined && (
              <span className={`text-xs ${task.autoAssign ? 'text-green-400' : 'text-slate-500'}`}>
                {task.autoAssign ? '⚡ 자동' : '✋ 수동'}
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1">
          {/* 상세보기 버튼 */}
          {onViewDetail && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onViewDetail(task.id);
              }}
              className="p-1 text-slate-400 hover:text-purple-400 transition-colors"
              title="상세보기"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
            </button>
          )}
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
          {!task.assignedAgentId && onAssignAgent && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowAssignModal(true);
              }}
              className="p-1 text-slate-400 hover:text-blue-400 transition-colors"
              title="Agent 할당"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
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
        <span>
          {task.status === 'pending' && '대기 중'}
          {task.status === 'in_progress' && '진행 중'}
          {task.status === 'completed' && '완료'}
          {task.status === 'cancelled' && '취소됨'}
        </span>
        <span>{new Date(task.createdAt).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' })}</span>
      </div>

      <AssignAgentModal
        isOpen={showAssignModal}
        onClose={() => setShowAssignModal(false)}
        onAssign={handleAssign}
        agents={agents}
        taskTitle={task.title}
      />
    </div>
  );
}

