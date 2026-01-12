import { useState } from 'react';
import type { Task, CreateTaskInput, TaskStatus, TaskPriority } from '../../types/task';
import type { Agent, Ticket, ApprovalRequest, AgentLog, LLMConfig, Interaction, TaskChatMessage } from '../../types';
import { TaskCard } from './TaskCard';
import { CreateTaskModal } from './CreateTaskModal';
import { AnalyzeMCPMessagesModal } from './AnalyzeMCPMessagesModal';
import { TaskDetailModal } from './TaskDetailModal';

interface TaskPanelProps {
  tasks: Task[];
  agents: Agent[];
  tickets?: Ticket[];
  approvalRequests?: ApprovalRequest[];
  agentLogs?: AgentLog[];
  interactions?: Interaction[];
  taskChatMessages?: TaskChatMessage[];
  onCreateTask: (task: CreateTaskInput) => void;
  onUpdateTask: (id: string, updates: Partial<Task>) => void;
  onDeleteTask: (id: string) => void;
  onClearAllTasks?: () => void;
  onDeleteCompletedTasks?: () => void;
  onClearAllLogs?: () => void;
  onAssignAgent?: (taskId: string, agentId: string) => void;
  onRespondInteraction?: (interactionId: string, response: string) => void;
  onSendTaskMessage?: (taskId: string, message: string) => void;
  availableMCPs: Array<{ id: string; type: string; name: string; status: string }>;
  llmConfig: LLMConfig;
  autoAssignMode?: 'global' | 'manual';
  onAutoAssignModeChange?: (mode: 'global' | 'manual') => void;
  // External modal control
  showCreateTaskModal?: boolean;
  onCloseCreateTaskModal?: () => void;
}

export function TaskPanel({
  tasks,
  agents,
  tickets = [],
  approvalRequests = [],
  agentLogs = [],
  interactions = [],
  taskChatMessages = [],
  onCreateTask,
  onUpdateTask,
  onDeleteTask,
  onClearAllTasks,
  onDeleteCompletedTasks,
  onClearAllLogs,
  onAssignAgent,
  onRespondInteraction,
  onSendTaskMessage,
  availableMCPs,
  llmConfig,
  autoAssignMode = 'manual',
  onAutoAssignModeChange = () => {},
  showCreateTaskModal,
  onCloseCreateTaskModal,
}: TaskPanelProps) {
  // Internal modal state (used if no external control provided)
  const [internalModalOpen, setInternalModalOpen] = useState(false);

  // Use external control if provided, otherwise use internal state
  const isCreateModalOpen = showCreateTaskModal ?? internalModalOpen;
  const setIsCreateModalOpen = onCloseCreateTaskModal
    ? (open: boolean) => { if (!open) onCloseCreateTaskModal(); }
    : setInternalModalOpen;

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [isAnalyzeModalOpen, setIsAnalyzeModalOpen] = useState(false);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [isManagementPanelOpen, setIsManagementPanelOpen] = useState(false);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<TaskStatus | 'all'>('all');
  const [filterPriority, setFilterPriority] = useState<TaskPriority | 'all'>('all');
  const [showAllTasks, setShowAllTasks] = useState(false);

  const filteredTasks = tasks.filter(task => {
    // Status filter
    if (filterStatus !== 'all' && task.status !== filterStatus) return false;
    // Priority filter
    if (filterPriority !== 'all' && task.priority !== filterPriority) return false;
    // Search query filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      const titleMatch = task.title.toLowerCase().includes(query);
      const descMatch = task.description?.toLowerCase().includes(query);
      const tagMatch = task.tags.some(tag => tag.toLowerCase().includes(query));
      if (!titleMatch && !descMatch && !tagMatch) return false;
    }
    return true;
  });

  const pendingTasks = filteredTasks.filter(t => t.status === 'pending');
  const inProgressTasks = filteredTasks.filter(t => t.status === 'in_progress');
  const completedTasks = filteredTasks.filter(t => t.status === 'completed');
  const cancelledTasks = filteredTasks.filter(t => t.status === 'cancelled');
  const failedTasksList = filteredTasks.filter(t => t.status === 'failed');

  // Count tasks by status for management panel
  const taskCounts = {
    total: tasks.length,
    pending: tasks.filter(t => t.status === 'pending').length,
    in_progress: tasks.filter(t => t.status === 'in_progress').length,
    completed: tasks.filter(t => t.status === 'completed').length,
    cancelled: tasks.filter(t => t.status === 'cancelled').length,
    failed: tasks.filter(t => t.status === 'failed').length,
  };

  // Attention metrics
  const tasksNeedingApproval = approvalRequests.filter(req =>
    tasks.some(t => t.assignedAgentId === req.agentId)
  ).length;
  const tasksWithoutAgent = tasks.filter(t => !t.assignedAgentId && t.status !== 'completed' && t.status !== 'cancelled').length;
  const failedTasks = tickets.filter(t => t.status === 'rejected').length;
  const pendingInteractions = interactions.filter(i => i.status === 'pending').length;

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
  const taskAgentLogs = selectedTaskId
    ? agentLogs.filter(log => 
        log.relatedTaskId === selectedTaskId || 
        log.agentId === selectedTask?.assignedAgentId
      )
    : [];
  const taskInteractions = selectedTaskId
    ? interactions.filter(i => i.taskId === selectedTaskId)
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

      {/* Attention Section */}
      {(tasksNeedingApproval > 0 || tasksWithoutAgent > 0 || failedTasks > 0 || pendingInteractions > 0) && (
        <div className="mb-6 p-4 bg-amber-500/10 border border-amber-500/30 rounded-lg">
          <div className="flex items-center gap-2 mb-3">
            <svg className="w-5 h-5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <h3 className="text-sm font-semibold text-amber-400">Needs Your Attention</h3>
          </div>
          <div className="space-y-2 text-sm">
            {tasksNeedingApproval > 0 && (
              <div className="flex items-center gap-2 text-white">
                <span className="w-2 h-2 rounded-full bg-amber-400"></span>
                <span><strong>{tasksNeedingApproval}</strong> approval{tasksNeedingApproval > 1 ? 's' : ''} waiting</span>
              </div>
            )}
            {pendingInteractions > 0 && (
              <div className="flex items-center gap-2 text-white">
                <span className="w-2 h-2 rounded-full bg-blue-400"></span>
                <span><strong>{pendingInteractions}</strong> interaction{pendingInteractions > 1 ? 's' : ''} pending</span>
              </div>
            )}
            {tasksWithoutAgent > 0 && (
              <div className="flex items-center gap-2 text-white">
                <span className="w-2 h-2 rounded-full bg-yellow-400"></span>
                <span><strong>{tasksWithoutAgent}</strong> task{tasksWithoutAgent > 1 ? 's' : ''} without agent</span>
              </div>
            )}
            {failedTasks > 0 && (
              <div className="flex items-center gap-2 text-white">
                <span className="w-2 h-2 rounded-full bg-red-400"></span>
                <span><strong>{failedTasks}</strong> rejected ticket{failedTasks > 1 ? 's' : ''}</span>
              </div>
            )}
          </div>
        </div>
      )}

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

        {/* Task Management Button */}
        <div className="relative">
          <button
            onClick={() => setIsManagementPanelOpen(!isManagementPanelOpen)}
            className={`px-6 py-3 ${isManagementPanelOpen ? 'bg-slate-600' : 'bg-slate-700 hover:bg-slate-600'} text-white rounded-lg transition-colors flex items-center justify-center gap-2 font-medium`}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            Task 관리
            {tasks.length > 0 && (
              <span className="ml-1 px-2 py-0.5 bg-slate-500 text-xs rounded-full">{tasks.length}</span>
            )}
          </button>

          {/* Management Dropdown */}
          {isManagementPanelOpen && (
            <div className="absolute top-full right-0 mt-2 w-72 bg-slate-800 border border-slate-600 rounded-lg shadow-xl z-50">
              <div className="p-4 border-b border-slate-600">
                <h4 className="text-sm font-semibold text-white mb-3">Task 현황</h4>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="flex justify-between px-2 py-1 bg-slate-700/50 rounded">
                    <span className="text-slate-400">전체</span>
                    <span className="text-white font-medium">{taskCounts.total}</span>
                  </div>
                  <div className="flex justify-between px-2 py-1 bg-yellow-500/10 rounded">
                    <span className="text-yellow-400">대기</span>
                    <span className="text-yellow-400 font-medium">{taskCounts.pending}</span>
                  </div>
                  <div className="flex justify-between px-2 py-1 bg-blue-500/10 rounded">
                    <span className="text-blue-400">진행</span>
                    <span className="text-blue-400 font-medium">{taskCounts.in_progress}</span>
                  </div>
                  <div className="flex justify-between px-2 py-1 bg-green-500/10 rounded">
                    <span className="text-green-400">완료</span>
                    <span className="text-green-400 font-medium">{taskCounts.completed}</span>
                  </div>
                  <div className="flex justify-between px-2 py-1 bg-slate-500/10 rounded">
                    <span className="text-slate-400">취소</span>
                    <span className="text-slate-400 font-medium">{taskCounts.cancelled}</span>
                  </div>
                  <div className="flex justify-between px-2 py-1 bg-red-500/10 rounded">
                    <span className="text-red-400">실패</span>
                    <span className="text-red-400 font-medium">{taskCounts.failed}</span>
                  </div>
                </div>
              </div>

              <div className="p-3 space-y-2">
                <button
                  onClick={() => {
                    setShowAllTasks(!showAllTasks);
                    setIsManagementPanelOpen(false);
                  }}
                  className="w-full px-3 py-2 text-sm text-left text-white hover:bg-slate-700 rounded flex items-center gap-2"
                >
                  <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
                  </svg>
                  {showAllTasks ? '카테고리별 보기' : '전체 Task 목록 보기'}
                </button>

                <hr className="border-slate-600" />

                <button
                  onClick={() => {
                    if (onDeleteCompletedTasks && taskCounts.completed > 0) {
                      if (confirm(`완료된 ${taskCounts.completed}개 Task를 삭제하시겠습니까?`)) {
                        onDeleteCompletedTasks();
                      }
                    }
                    setIsManagementPanelOpen(false);
                  }}
                  disabled={taskCounts.completed === 0}
                  className="w-full px-3 py-2 text-sm text-left text-green-400 hover:bg-slate-700 rounded flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  완료된 Task 삭제 ({taskCounts.completed})
                </button>

                <button
                  onClick={() => {
                    if (onClearAllLogs) {
                      if (confirm('모든 로그를 삭제하시겠습니까?')) {
                        onClearAllLogs();
                      }
                    }
                    setIsManagementPanelOpen(false);
                  }}
                  className="w-full px-3 py-2 text-sm text-left text-amber-400 hover:bg-slate-700 rounded flex items-center gap-2"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  모든 로그 삭제
                </button>

                <hr className="border-slate-600" />

                <button
                  onClick={() => {
                    if (onClearAllTasks && taskCounts.total > 0) {
                      if (confirm(`정말로 모든 ${taskCounts.total}개 Task를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.`)) {
                        onClearAllTasks();
                      }
                    }
                    setIsManagementPanelOpen(false);
                  }}
                  disabled={taskCounts.total === 0}
                  className="w-full px-3 py-2 text-sm text-left text-red-400 hover:bg-slate-700 rounded flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                  모든 Task 삭제 ({taskCounts.total})
                </button>
              </div>
            </div>
          )}
        </div>
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

      {/* Search and Filters */}
      <div className="flex flex-col sm:flex-row gap-3 mb-4">
        {/* Search Input */}
        <div className="relative flex-1">
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Task 검색 (제목, 설명, 태그)..."
            className="w-full pl-10 pr-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white text-sm placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        {/* Filter Dropdowns */}
        <div className="flex gap-2">
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value as TaskStatus | 'all')}
            className="px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
          >
            <option value="all">전체 상태</option>
            <option value="pending">대기 중</option>
            <option value="in_progress">진행 중</option>
            <option value="completed">완료</option>
            <option value="cancelled">취소됨</option>
            <option value="failed">실패</option>
          </select>
          <select
            value={filterPriority}
            onChange={(e) => setFilterPriority(e.target.value as TaskPriority | 'all')}
            className="px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
          >
            <option value="all">전체 우선순위</option>
            <option value="low">낮음</option>
            <option value="medium">보통</option>
            <option value="high">높음</option>
            <option value="urgent">긴급</option>
          </select>
        </div>
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
        ) : showAllTasks ? (
          /* 전체 Task 목록 보기 */
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-slate-300 uppercase flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-slate-400"></span>
                전체 Task ({filteredTasks.length})
              </h3>
              <button
                onClick={() => setShowAllTasks(false)}
                className="text-xs text-blue-400 hover:text-blue-300"
              >
                카테고리별 보기
              </button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredTasks.map(task => (
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
                  taskChatMessages={taskChatMessages}
                  onSendTaskMessage={onSendTaskMessage}
                />
              ))}
            </div>
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
                      taskChatMessages={taskChatMessages}
                      onSendTaskMessage={onSendTaskMessage}
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
                      taskChatMessages={taskChatMessages}
                      onSendTaskMessage={onSendTaskMessage}
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
                      taskChatMessages={taskChatMessages}
                      onSendTaskMessage={onSendTaskMessage}
                    />
                  ))}
                </div>
              </div>
            )}

            {cancelledTasks.length > 0 && (
              <div className="mt-6">
                <h3 className="text-sm font-semibold text-slate-300 uppercase mb-3 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-slate-500"></span>
                  취소됨 ({cancelledTasks.length})
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {cancelledTasks.map(task => (
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
                      taskChatMessages={taskChatMessages}
                      onSendTaskMessage={onSendTaskMessage}
                    />
                  ))}
                </div>
              </div>
            )}

            {failedTasksList.length > 0 && (
              <div className="mt-6">
                <h3 className="text-sm font-semibold text-slate-300 uppercase mb-3 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-red-500"></span>
                  실패 ({failedTasksList.length})
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {failedTasksList.map(task => (
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
                      taskChatMessages={taskChatMessages}
                      onSendTaskMessage={onSendTaskMessage}
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
          allAgents={agents}
          tickets={taskTickets}
          approvalRequests={taskApprovals}
          agentLogs={taskAgentLogs}
          interactions={taskInteractions}
          onRespondInteraction={onRespondInteraction}
          taskChatMessages={taskChatMessages.filter(msg => msg.taskId === selectedTask.id)}
          onSendTaskMessage={onSendTaskMessage}
        />
      )}
    </div>
  );
}

