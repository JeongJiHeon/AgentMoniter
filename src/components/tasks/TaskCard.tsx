/**
 * TaskCard - Terminal Elegance 디자인의 Task 카드
 */

import React from 'react'
import type { Task, TaskStatus, TaskPriority } from '../../types/task'
import type { Agent, TaskChatMessage } from '../../types'
import { getStatusColor, getStatusLabel, getStatusIcon } from '../../types/agentResult'
import { AssignAgentModal } from './AssignAgentModal'
import { TaskChatDrawer } from './TaskChatDrawer'
import { cn } from '@/lib/utils'
import { Button } from '../ui/Button'
import { X, MessageSquare, Zap, Square, Eye, UserPlus, Clock, CheckCircle2, XCircle, AlertCircle, Play } from 'lucide-react'

interface TaskCardProps {
  task: Task
  agents: Agent[]
  onStatusChange: (id: string, status: TaskStatus) => void
  onUpdate: (id: string, updates: Partial<Task>) => void
  onDelete: (id: string) => void
  onAssignAgent?: (taskId: string, agentId: string) => void
  onViewDetail?: (taskId: string) => void
  autoAssignMode?: 'global' | 'manual'
  taskChatMessages?: TaskChatMessage[]
  onSendTaskMessage?: (taskId: string, message: string) => void
}

const priorityConfig: Record<TaskPriority, { label: string; color: string; bgColor: string; borderColor: string }> = {
  low: {
    label: 'Low',
    color: 'text-[hsl(var(--muted-foreground))]',
    bgColor: 'bg-[hsl(var(--muted))]',
    borderColor: 'border-[hsl(var(--border))]',
  },
  medium: {
    label: 'Medium',
    color: 'text-[hsl(var(--info))]',
    bgColor: 'bg-[hsl(var(--info))]/10',
    borderColor: 'border-[hsl(var(--info))]/20',
  },
  high: {
    label: 'High',
    color: 'text-[hsl(var(--warning))]',
    bgColor: 'bg-[hsl(var(--warning))]/10',
    borderColor: 'border-[hsl(var(--warning))]/20',
  },
  urgent: {
    label: 'Urgent',
    color: 'text-[hsl(var(--destructive))]',
    bgColor: 'bg-[hsl(var(--destructive))]/10',
    borderColor: 'border-[hsl(var(--destructive))]/20',
  },
}

const statusConfig: Record<TaskStatus, { icon: React.ReactNode; color: string; borderColor: string }> = {
  pending: {
    icon: <Clock className="w-3.5 h-3.5" />,
    color: 'text-[hsl(var(--muted-foreground))]',
    borderColor: 'border-l-[hsl(var(--muted-foreground))]',
  },
  in_progress: {
    icon: <Play className="w-3.5 h-3.5" />,
    color: 'text-[hsl(var(--info))]',
    borderColor: 'border-l-[hsl(var(--info))]',
  },
  completed: {
    icon: <CheckCircle2 className="w-3.5 h-3.5" />,
    color: 'text-[hsl(var(--success))]',
    borderColor: 'border-l-[hsl(var(--success))]',
  },
  cancelled: {
    icon: <XCircle className="w-3.5 h-3.5" />,
    color: 'text-[hsl(var(--muted-foreground))]',
    borderColor: 'border-l-[hsl(var(--muted-foreground))]',
  },
  failed: {
    icon: <AlertCircle className="w-3.5 h-3.5" />,
    color: 'text-[hsl(var(--destructive))]',
    borderColor: 'border-l-[hsl(var(--destructive))]',
  },
}

const getActionMessage = (task: Task, assignedAgent?: Agent, allAgents?: Agent[]): string => {
  if (task.status === 'completed') return 'Completed'
  if (task.status === 'cancelled') return 'Cancelled'
  if (task.status === 'failed') return 'Failed'
  if (!task.assignedAgentId) return 'No agent assigned'
  if (task.status === 'pending') return 'Waiting to start'
  if (task.status === 'in_progress') {
    if (assignedAgent?.thinkingMode === 'idle') return 'Agent idle'
    if (assignedAgent?.role === 'orchestration' && assignedAgent.subAgents && assignedAgent.subAgents.length > 0) {
      const activeSubAgents = assignedAgent.subAgents.filter(subId =>
        allAgents?.find(a => a.id === subId && a.isActive)
      ).length
      return `Running with ${activeSubAgents} agent${activeSubAgents !== 1 ? 's' : ''}`
    }
    return 'Running'
  }
  return 'Unknown status'
}

export function TaskCard({
  task,
  agents,
  onStatusChange,
  onUpdate,
  onDelete,
  onAssignAgent,
  onViewDetail,
  autoAssignMode = 'manual',
  taskChatMessages = [],
  onSendTaskMessage,
}: TaskCardProps) {
  const [showAssignModal, setShowAssignModal] = React.useState(false)
  const [showChatDrawer, setShowChatDrawer] = React.useState(false)
  const [userResponse, setUserResponse] = React.useState('')

  const assignedAgent = agents.find(a => a.id === task.assignedAgentId)
  const actionMessage = getActionMessage(task, assignedAgent, agents)
  const taskMessages = taskChatMessages.filter(msg => msg.taskId === task.id)
  const isFinished = task.status === 'completed' || task.status === 'cancelled' || task.status === 'failed'

  const handleAssign = (agentId: string) => {
    if (onAssignAgent) {
      onAssignAgent(task.id, agentId)
      onUpdate(task.id, { assignedAgentId: agentId, status: 'in_progress' })
    }
  }

  const handleUserResponse = () => {
    if (userResponse.trim() && onSendTaskMessage) {
      onSendTaskMessage(task.id, userResponse.trim())
      setUserResponse('')
    }
  }

  return (
    <div
      className={cn(
        'group relative overflow-hidden rounded-xl',
        'bg-[hsl(var(--card))] border border-[hsl(var(--border))]',
        'border-l-4 transition-all duration-300',
        statusConfig[task.status].borderColor,
        isFinished && 'opacity-60',
        'hover:shadow-lg hover:border-[hsl(var(--border))]/80'
      )}
    >
      {/* Hover Gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-[hsl(var(--primary))]/5 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

      <div className="relative p-4">
        {/* Header */}
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex-1 min-w-0">
            {/* Title */}
            <h4 className="text-sm font-semibold text-[hsl(var(--foreground))] truncate mb-1.5">
              {task.title}
            </h4>

            {/* Status & Priority Badges */}
            <div className="flex items-center gap-2 flex-wrap">
              {/* Status Badge */}
              <span className={cn(
                'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md',
                'text-[10px] font-mono font-medium uppercase tracking-wider',
                statusConfig[task.status].color,
                'bg-[hsl(var(--muted))]/50 border border-[hsl(var(--border))]'
              )}>
                {statusConfig[task.status].icon}
                {task.status.replace('_', ' ')}
              </span>

              {/* Priority Badge */}
              <span className={cn(
                'inline-flex items-center px-2 py-0.5 rounded-md',
                'text-[10px] font-mono font-medium uppercase tracking-wider',
                priorityConfig[task.priority].color,
                priorityConfig[task.priority].bgColor,
                'border',
                priorityConfig[task.priority].borderColor
              )}>
                {priorityConfig[task.priority].label}
              </span>
            </div>
          </div>

          {/* Right Actions */}
          <div className="flex flex-col items-center gap-1">
            {autoAssignMode === 'manual' && task.autoAssign !== undefined && (
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  onUpdate(task.id, { autoAssign: !task.autoAssign })
                }}
                className={cn(
                  'p-1.5 rounded-lg transition-all duration-200',
                  'hover:bg-[hsl(var(--muted))]',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--ring))]',
                  task.autoAssign
                    ? 'text-[hsl(var(--success))] bg-[hsl(var(--success))]/10'
                    : 'text-[hsl(var(--muted-foreground))]'
                )}
                title={task.autoAssign ? 'Auto-assign ON' : 'Auto-assign OFF'}
              >
                {task.autoAssign ? <Zap className="w-4 h-4" /> : <Square className="w-4 h-4" />}
              </button>
            )}
            <button
              onClick={(e) => {
                e.stopPropagation()
                onDelete(task.id)
              }}
              className={cn(
                'p-1.5 rounded-lg transition-all duration-200',
                'text-[hsl(var(--muted-foreground))]',
                'hover:text-[hsl(var(--destructive))] hover:bg-[hsl(var(--destructive))]/10',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--ring))]'
              )}
              title="Delete"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Description */}
        {task.description && (
          <p className="text-xs text-[hsl(var(--muted-foreground))] line-clamp-2 mb-3 leading-relaxed">
            {task.description}
          </p>
        )}

        {/* Tags */}
        {task.tags.length > 0 && (
          <div className="flex items-center gap-1.5 flex-wrap mb-3">
            {task.tags.slice(0, 3).map((tag, idx) => (
              <span
                key={idx}
                className={cn(
                  'px-2 py-0.5 rounded text-[10px] font-mono',
                  'bg-[hsl(var(--muted))]/50 text-[hsl(var(--muted-foreground))]',
                  'border border-[hsl(var(--border))]'
                )}
              >
                #{tag}
              </span>
            ))}
            {task.tags.length > 3 && (
              <span className="text-[10px] text-[hsl(var(--muted-foreground))] font-mono">
                +{task.tags.length - 3}
              </span>
            )}
          </div>
        )}

        {/* Action Message */}
        <div className={cn(
          'flex items-center gap-2 mb-3 text-xs font-medium',
          !task.assignedAgentId && 'text-[hsl(var(--warning))]',
          task.status === 'completed' && 'text-[hsl(var(--success))]',
          task.status === 'in_progress' && 'text-[hsl(var(--info))]',
          task.status === 'pending' && 'text-[hsl(var(--muted-foreground))]',
          task.status === 'failed' && 'text-[hsl(var(--destructive))]'
        )}>
          <span>{actionMessage}</span>
          {assignedAgent && task.status === 'in_progress' && (
            <span className="text-[hsl(var(--muted-foreground))] font-normal">
              ({assignedAgent.name})
            </span>
          )}
        </div>

        {/* Agent Lifecycle Status */}
        {task.agentLifecycleStatus && (
          <div className="mb-3">
            <span
              className={cn(
                'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold',
                getStatusColor(task.agentLifecycleStatus)
              )}
            >
              <span>{getStatusIcon(task.agentLifecycleStatus)}</span>
              <span>{getStatusLabel(task.agentLifecycleStatus)}</span>
            </span>
          </div>
        )}

        {/* Pending Question */}
        {task.pendingQuestion && task.agentLifecycleStatus === 'WAITING_USER' && (
          <div className={cn(
            'mb-3 p-3 rounded-lg',
            'bg-[hsl(var(--warning))]/5 border border-[hsl(var(--warning))]/20'
          )}>
            <div className="flex items-center gap-2 mb-2">
              <AlertCircle className="w-4 h-4 text-[hsl(var(--warning))]" />
              <p className="text-xs font-semibold text-[hsl(var(--warning))]">Agent Question</p>
            </div>
            <p className="text-xs text-[hsl(var(--foreground))] mb-3 leading-relaxed">
              {task.pendingQuestion}
            </p>
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={userResponse}
                onChange={(e) => setUserResponse(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleUserResponse()}
                placeholder="Type your answer..."
                className={cn(
                  'flex-1 h-8 px-3 rounded-lg text-xs font-mono',
                  'bg-[hsl(var(--background))] border border-[hsl(var(--border))]',
                  'text-[hsl(var(--foreground))] placeholder:text-[hsl(var(--muted-foreground))]',
                  'focus:outline-none focus:ring-2 focus:ring-[hsl(var(--warning))]/50',
                  'transition-all duration-200'
                )}
              />
              <Button
                size="sm"
                onClick={handleUserResponse}
                disabled={!userResponse.trim()}
                className="h-8"
              >
                Send
              </Button>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex items-center gap-2 flex-wrap">
          {onSendTaskMessage && (
            <Button
              variant="secondary"
              size="sm"
              onClick={(e) => {
                e.stopPropagation()
                setShowChatDrawer(true)
              }}
              className="h-7 text-xs"
            >
              <MessageSquare className="w-3 h-3 mr-1" />
              Chat
              {taskMessages.length > 0 && (
                <span className={cn(
                  'ml-1.5 min-w-4 h-4 px-1 rounded text-[10px] font-mono',
                  'bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))]'
                )}>
                  {taskMessages.length}
                </span>
              )}
            </Button>
          )}
          {onViewDetail && (
            <Button
              variant="secondary"
              size="sm"
              onClick={(e) => {
                e.stopPropagation()
                onViewDetail(task.id)
              }}
              className="h-7 text-xs"
            >
              <Eye className="w-3 h-3 mr-1" />
              Detail
            </Button>
          )}
          {!task.assignedAgentId && onAssignAgent && (
            <Button
              variant="default"
              size="sm"
              onClick={(e) => {
                e.stopPropagation()
                setShowAssignModal(true)
              }}
              className="h-7 text-xs"
            >
              <UserPlus className="w-3 h-3 mr-1" />
              Assign
            </Button>
          )}
          {!isFinished && (
            <Button
              variant="ghost"
              size="sm"
              onClick={(e) => {
                e.stopPropagation()
                onStatusChange(task.id, 'cancelled')
              }}
              className={cn(
                'h-7 text-xs',
                'text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--destructive))]'
              )}
            >
              Cancel
            </Button>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className={cn(
        'px-4 py-2 border-t border-[hsl(var(--border))]',
        'bg-[hsl(var(--muted))]/30'
      )}>
        <div className="flex items-center justify-between text-[10px] text-[hsl(var(--muted-foreground))] font-mono">
          <span>
            {new Date(task.createdAt).toLocaleDateString('en-US', {
              month: 'short',
              day: 'numeric',
              year: 'numeric'
            })}
          </span>
          {task.source !== 'manual' && (
            <span className="uppercase tracking-wider">
              {task.source}
            </span>
          )}
        </div>
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
  )
}
