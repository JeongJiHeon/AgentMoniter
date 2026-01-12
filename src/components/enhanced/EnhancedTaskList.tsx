import { useMemo } from 'react';
import { Circle, CheckCircle2, XCircle, Clock, AlertTriangle, Zap, TrendingUp, X } from 'lucide-react';
import type { Task } from '../../types/task';
import type { Agent } from '../../types';

interface EnhancedTaskListProps {
  tasks: Task[];
  selectedTaskId: string | null;
  onSelectTask: (taskId: string) => void;
  searchQuery: string;
  agents: Agent[];
  onUpdateTask: (id: string, updates: Partial<Task>) => void;
  onDeleteTask: (id: string) => void;
}

export function EnhancedTaskList({
  tasks,
  selectedTaskId,
  onSelectTask,
  searchQuery,
  agents,
  onDeleteTask,
}: EnhancedTaskListProps) {
  // Filter and sort tasks
  const filteredTasks = useMemo(() => {
    let filtered = tasks;

    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(task =>
        task.title.toLowerCase().includes(query) ||
        task.description?.toLowerCase().includes(query) ||
        task.tags.some(tag => tag.toLowerCase().includes(query))
      );
    }

    // Sort: in_progress first, then pending, then others
    return filtered.sort((a, b) => {
      const statusOrder = { in_progress: 0, pending: 1, failed: 2, completed: 3, cancelled: 4 };
      return statusOrder[a.status] - statusOrder[b.status];
    });
  }, [tasks, searchQuery]);

  // Group by status
  const groupedTasks = useMemo(() => {
    const groups: Record<string, Task[]> = {
      in_progress: [],
      pending: [],
      completed: [],
      failed: [],
      cancelled: [],
    };

    filteredTasks.forEach(task => {
      groups[task.status]?.push(task);
    });

    return groups;
  }, [filteredTasks]);

  return (
    <div className="h-full flex flex-col bg-gradient-to-br from-[#1a1f2e]/50 to-[#0d1117]/50 border border-cyan-400/10 rounded-xl backdrop-blur-xl overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-cyan-400/10">
        <h2 className="text-sm font-bold text-cyan-300 tracking-wider uppercase">Task Queue</h2>
        <p className="text-xs text-gray-500 mt-0.5">{filteredTasks.length} task{filteredTasks.length !== 1 ? 's' : ''}</p>
      </div>

      {/* Task List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {Object.entries(groupedTasks).map(([status, statusTasks]) => {
          if (statusTasks.length === 0) return null;

          return (
            <div key={status} className="space-y-2">
              {/* Status header */}
              <div className="flex items-center gap-2 px-2 py-1">
                <StatusIcon status={status as Task['status']} />
                <span className="text-xs font-medium text-gray-400 uppercase tracking-wide">
                  {status.replace('_', ' ')} ({statusTasks.length})
                </span>
              </div>

              {/* Tasks */}
              {statusTasks.map(task => (
                <TaskCard
                  key={task.id}
                  task={task}
                  isSelected={task.id === selectedTaskId}
                  onClick={() => onSelectTask(task.id)}
                  onDelete={() => onDeleteTask(task.id)}
                  agent={agents.find(a => a.id === task.assignedAgentId)}
                />
              ))}
            </div>
          );
        })}

        {filteredTasks.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-gray-600">
            <Circle className="w-12 h-12 mb-3 opacity-30" />
            <p className="text-sm">No tasks found</p>
          </div>
        )}
      </div>
    </div>
  );
}

interface TaskCardProps {
  task: Task;
  isSelected: boolean;
  onClick: () => void;
  onDelete: () => void;
  agent?: Agent;
}

function TaskCard({ task, isSelected, onClick, onDelete, agent }: TaskCardProps) {
  const priorityColors = {
    low: 'border-gray-600/30 bg-gray-800/20',
    medium: 'border-cyan-500/30 bg-cyan-500/5',
    high: 'border-amber-500/30 bg-amber-500/5',
    urgent: 'border-red-500/50 bg-red-500/10',
  };

  const priorityGlow = {
    low: '',
    medium: 'shadow-cyan-500/10',
    high: 'shadow-amber-500/10',
    urgent: 'shadow-red-500/20 animate-pulse',
  };

  // Mock confidence and complexity (these would come from Enhanced Planner)
  const confidence = task.status === 'completed' ? 0.95 : task.status === 'in_progress' ? 0.78 : 0.65;
  const complexity = task.priority === 'urgent' ? 8 : task.priority === 'high' ? 6 : task.priority === 'medium' ? 4 : 2;

  return (
    <button
      onClick={onClick}
      className={`
        w-full text-left p-3 rounded-lg border transition-all duration-200
        ${priorityColors[task.priority]}
        ${isSelected
          ? 'border-cyan-400 shadow-lg shadow-cyan-500/30 bg-gradient-to-br from-cyan-500/10 to-magenta-500/5'
          : `hover:border-cyan-400/50 ${priorityGlow[task.priority]}`
        }
      `}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-medium text-gray-200 truncate">{task.title}</h3>
          {task.description && (
            <p className="text-xs text-gray-500 line-clamp-2 mt-0.5">{task.description}</p>
          )}
        </div>
        <div className="flex items-center gap-1.5">
          <PriorityBadge priority={task.priority} />
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            className="p-1 rounded hover:bg-red-500/20 text-gray-400 hover:text-red-400 transition-colors"
            title="Delete task"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Progress Bars */}
      {task.status === 'in_progress' && (
        <div className="space-y-1.5 mb-2">
          {/* Confidence */}
          <div className="space-y-0.5">
            <div className="flex items-center justify-between text-[10px] text-gray-500">
              <span>Confidence</span>
              <span className="tabular-nums">{(confidence * 100).toFixed(0)}%</span>
            </div>
            <div className="h-1 bg-gray-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-cyan-500 to-cyan-400 transition-all duration-500"
                style={{ width: `${confidence * 100}%` }}
              />
            </div>
          </div>

          {/* Complexity */}
          <div className="space-y-0.5">
            <div className="flex items-center justify-between text-[10px] text-gray-500">
              <span>Complexity</span>
              <span className="tabular-nums">{complexity}/10</span>
            </div>
            <div className="flex gap-0.5">
              {Array.from({ length: 10 }).map((_, i) => (
                <div
                  key={i}
                  className={`h-1 flex-1 rounded-sm ${
                    i < complexity
                      ? 'bg-gradient-to-r from-magenta-500 to-magenta-400'
                      : 'bg-gray-800'
                  }`}
                />
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between text-[10px] text-gray-500">
        <div className="flex items-center gap-2">
          {agent && (
            <div className="flex items-center gap-1 px-1.5 py-0.5 bg-cyan-500/10 border border-cyan-400/20 rounded text-cyan-300">
              <Zap className="w-2.5 h-2.5" />
              <span>{agent.name}</span>
            </div>
          )}
          {task.tags.length > 0 && (
            <span className="opacity-70">#{task.tags[0]}</span>
          )}
        </div>
        <time className="opacity-50" dateTime={task.createdAt.toISOString()}>
          {formatRelativeTime(task.createdAt)}
        </time>
      </div>
    </button>
  );
}

function StatusIcon({ status }: { status: Task['status'] }) {
  const icons = {
    pending: <Clock className="w-3 h-3 text-amber-400" />,
    in_progress: <TrendingUp className="w-3 h-3 text-green-400 animate-pulse" />,
    completed: <CheckCircle2 className="w-3 h-3 text-emerald-400" />,
    failed: <XCircle className="w-3 h-3 text-red-400" />,
    cancelled: <Circle className="w-3 h-3 text-gray-500" />,
  };

  return icons[status];
}

function PriorityBadge({ priority }: { priority: Task['priority'] }) {
  const colors = {
    low: 'bg-gray-700/50 text-gray-400',
    medium: 'bg-cyan-500/20 text-cyan-300',
    high: 'bg-amber-500/20 text-amber-300',
    urgent: 'bg-red-500/20 text-red-300 animate-pulse',
  };

  const icons = {
    low: null,
    medium: null,
    high: <AlertTriangle className="w-2.5 h-2.5" />,
    urgent: <AlertTriangle className="w-2.5 h-2.5" />,
  };

  return (
    <div className={`flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium uppercase ${colors[priority]}`}>
      {icons[priority]}
      {priority}
    </div>
  );
}

function formatRelativeTime(date: Date): string {
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  return `${days}d ago`;
}
