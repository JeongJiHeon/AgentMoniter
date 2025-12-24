import { useState } from 'react';
import type { Task, CreateTaskInput, TaskStatus, TaskPriority } from '../../types/task';
import type { Agent, Ticket, ApprovalRequest } from '../../types';
import { TaskCard } from './TaskCard';
import { CreateTaskModal } from './CreateTaskModal';
import { AnalyzeMCPMessagesModal } from './AnalyzeMCPMessagesModal';
import { TaskDetailModal } from './TaskDetailModal';

interface TaskPanelProps {
  tasks: Task[];
  agents: Agent[];
  tickets?: Ticket[];
  approvalRequests?: ApprovalRequest[];
  onCreateTask: (task: CreateTaskInput) => void;
  onUpdateTask: (id: string, updates: Partial<Task>) => void;
  onDeleteTask: (id: string) => void;
  onAssignAgent?: (taskId: string, agentId: string) => void;
  availableMCPs: Array<{ id: string; type: string; name: string; status: string }>;
  llmConfig: { provider: string; model: string; apiKey?: string };
  autoAssignMode?: 'global' | 'manual';
  onAutoAssignModeChange?: (mode: 'global' | 'manual') => void;
}

export function TaskPanel({
  tasks,
  agents,
  tickets = [],
  approvalRequests = [],
  onCreateTask,
  onUpdateTask,
  onDeleteTask,
  onAssignAgent,
  availableMCPs,
  llmConfig,
  autoAssignMode = 'manual',
  onAutoAssignModeChange = () => {},
}: TaskPanelProps) {
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isAnalyzeModalOpen, setIsAnalyzeModalOpen] = useState(false);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<TaskStatus | 'all'>('all');
  const [filterPriority, setFilterPriority] = useState<TaskPriority | 'all'>('all');

  const filteredTasks = tasks.filter(task => {
    if (filterStatus !== 'all' && task.status !== filterStatus) return false;
    if (filterPriority !== 'all' && task.priority !== filterPriority) return false;
    return true;
  });

  const pendingTasks = filteredTasks.filter(t => t.status === 'pending');
  const inProgressTasks = filteredTasks.filter(t => t.status === 'in_progress');
  const completedTasks = filteredTasks.filter(t => t.status === 'completed');

  const handleStatusChange = (taskId: string, newStatus: TaskStatus) => {
    const updates: Partial<Task> = { status: newStatus };
    if (newStatus === 'completed') {
      updates.completedAt = new Date();
    }
    onUpdateTask(taskId, updates);
  };

  const handleViewDetail = (taskId: string) => {
    setSelectedTaskId(taskId);
    setIsDetailModalOpen(true);
  };

  const selectedTask = tasks.find(t => t.id === selectedTaskId);
  const selectedAgent = selectedTask?.assignedAgentId
    ? agents.find(a => a.id === selectedTask.assignedAgentId)
    : undefined;
  const taskTickets = selectedTaskId
    ? tickets.filter(t => t.agentId === selectedTask?.assignedAgentId)
    : [];
  const taskApprovals = selectedTaskId
    ? approvalRequests.filter(a => a.agentId === selectedTask?.assignedAgentId)
    : [];

  return (
    <div className="bg-slate-800/50 rounded-xl p-6 border border-slate-700 flex flex-col" style={{ minHeight: 'calc(100vh - 200px)' }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-semibold text-white mb-1">Tasks</h2>
          <p className="text-sm text-slate-400">작업을 관리하고 MCP 메시지를 분석하여 Task로 변환하세요</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-slate-400">
            진행 중: <span className="text-white font-medium">{tasks.filter(t => t.status !== 'completed').length}</span> / 전체: <span className="text-white font-medium">{tasks.length}</span>
          </span>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-3 mb-6">
        <button
          onClick={() => setIsCreateModalOpen(true)}
          className="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors flex items-center justify-center gap-2 font-medium"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          새 Task 생성
        </button>
        <button
          onClick={() => setIsAnalyzeModalOpen(true)}
          className="px-6 py-3 bg-purple-600 hover:bg-purple-500 text-white rounded-lg transition-colors flex items-center justify-center gap-2 font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          disabled={availableMCPs.filter(mcp => mcp.status === 'connected').length === 0}
          title={availableMCPs.filter(mcp => mcp.status === 'connected').length === 0 ? '연결된 MCP 서비스가 없습니다' : 'MCP 메시지 분석'}
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
          </svg>
          MCP 메시지 분석
        </button>
      </div>

      {/* 자동 할당 토글 */}
      <div className="mb-4 p-3 bg-slate-700/50 border border-slate-600 rounded-lg flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-white">자동 할당 모드</p>
          <p className="text-xs text-slate-400 mt-1">
            {autoAssignMode === 'global' 
              ? '모든 Task를 자동으로 Agent에게 할당합니다'
              : 'Task별로 자동 할당 여부를 설정할 수 있습니다'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-slate-800 rounded-lg p-1">
            <button
              onClick={() => onAutoAssignModeChange('global')}
              className={`px-3 py-1.5 text-xs font-medium rounded transition-colors ${
                autoAssignMode === 'global'
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              자동 모드
            </button>
            <button
              onClick={() => onAutoAssignModeChange('manual')}
              className={`px-3 py-1.5 text-xs font-medium rounded transition-colors ${
                autoAssignMode === 'manual'
                  ? 'bg-slate-600 text-white'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              수동 모드
            </button>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-2 mb-4">
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value as TaskStatus | 'all')}
          className="flex-1 px-2 py-1 bg-slate-700 border border-slate-600 rounded text-white text-xs focus:outline-none focus:border-blue-500"
        >
          <option value="all">전체 상태</option>
          <option value="pending">대기 중</option>
          <option value="in_progress">진행 중</option>
          <option value="completed">완료</option>
        </select>
        <select
          value={filterPriority}
          onChange={(e) => setFilterPriority(e.target.value as TaskPriority | 'all')}
          className="flex-1 px-2 py-1 bg-slate-700 border border-slate-600 rounded text-white text-xs focus:outline-none focus:border-blue-500"
        >
          <option value="all">전체 우선순위</option>
          <option value="low">낮음</option>
          <option value="medium">보통</option>
          <option value="high">높음</option>
          <option value="urgent">긴급</option>
        </select>
      </div>

      {/* Task List */}
      <div className="flex-1 overflow-y-auto space-y-6">
        {filteredTasks.length === 0 ? (
          <div className="text-center py-16 text-slate-500">
            <svg className="w-16 h-16 mx-auto mb-4 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            <p className="text-lg font-medium mb-2">
              {tasks.length === 0 ? '등록된 Task가 없습니다' : '필터 조건에 맞는 Task가 없습니다'}
            </p>
            <p className="text-sm text-slate-600">
              {tasks.length === 0 && '새 Task를 생성하거나 MCP 메시지를 분석해보세요'}
            </p>
          </div>
        ) : (
          <>
            {pendingTasks.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-slate-300 uppercase mb-3 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-yellow-500"></span>
                  대기 중 ({pendingTasks.length})
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {pendingTasks.map(task => (
                    <TaskCard
                      key={task.id}
                      task={task}
                      agents={agents}
                      onStatusChange={handleStatusChange}
                      onUpdate={onUpdateTask}
                      onDelete={onDeleteTask}
                      onAssignAgent={onAssignAgent}
                      onViewDetail={handleViewDetail}
                      autoAssignMode={autoAssignMode}
                    />
                  ))}
                </div>
              </div>
            )}

            {inProgressTasks.length > 0 && (
              <div className="mt-6">
                <h3 className="text-sm font-semibold text-slate-300 uppercase mb-3 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                  진행 중 ({inProgressTasks.length})
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {inProgressTasks.map(task => (
                    <TaskCard
                      key={task.id}
                      task={task}
                      agents={agents}
                      onStatusChange={handleStatusChange}
                      onUpdate={onUpdateTask}
                      onDelete={onDeleteTask}
                      onAssignAgent={onAssignAgent}
                      onViewDetail={handleViewDetail}
                      autoAssignMode={autoAssignMode}
                    />
                  ))}
                </div>
              </div>
            )}

            {completedTasks.length > 0 && (
              <div className="mt-6">
                <h3 className="text-sm font-semibold text-slate-300 uppercase mb-3 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-green-500"></span>
                  완료 ({completedTasks.length})
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {completedTasks.map(task => (
                    <TaskCard
                      key={task.id}
                      task={task}
                      agents={agents}
                      onStatusChange={handleStatusChange}
                      onUpdate={onUpdateTask}
                      onDelete={onDeleteTask}
                      onAssignAgent={onAssignAgent}
                      onViewDetail={handleViewDetail}
                      autoAssignMode={autoAssignMode}
                    />
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Modals */}
      <CreateTaskModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onCreateTask={onCreateTask}
        defaultAutoAssign={autoAssignMode === 'global'}
      />

      <AnalyzeMCPMessagesModal
        isOpen={isAnalyzeModalOpen}
        onClose={() => setIsAnalyzeModalOpen(false)}
        onCreateTasks={(tasks) => {
          tasks.forEach(task => onCreateTask(task));
          setIsAnalyzeModalOpen(false);
        }}
        availableMCPs={availableMCPs}
        llmConfig={llmConfig}
      />

      {selectedTask && (
        <TaskDetailModal
          isOpen={isDetailModalOpen}
          onClose={() => setIsDetailModalOpen(false)}
          task={selectedTask}
          agent={selectedAgent}
          tickets={taskTickets}
          approvalRequests={taskApprovals}
        />
      )}
    </div>
  );
}

