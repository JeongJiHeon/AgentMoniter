/**
 * KPIDashboard - Terminal Elegance 디자인의 KPI 대시보드
 */

import { useMemo } from 'react'
import { useTaskStore, useTicketStore } from '../../stores'
import { useAllAgents } from '../../hooks/useAllAgents'
import { cn } from '@/lib/utils'
import { Users, ListTodo, TrendingUp, Clock, Activity, Zap } from 'lucide-react'

interface KPICardProps {
  title: string
  value: string | number
  subtitle?: string
  icon: React.ReactNode
  accentColor: 'primary' | 'success' | 'warning' | 'info'
  footer?: React.ReactNode
  trend?: {
    value: number
    label: string
  }
}

const accentColors = {
  primary: {
    bg: 'bg-[hsl(var(--primary))]/10',
    text: 'text-[hsl(var(--primary))]',
    border: 'border-[hsl(var(--primary))]/20',
    glow: 'shadow-[hsl(var(--primary))]/10',
    gradient: 'from-[hsl(var(--primary))]/20 to-transparent',
  },
  success: {
    bg: 'bg-[hsl(var(--success))]/10',
    text: 'text-[hsl(var(--success))]',
    border: 'border-[hsl(var(--success))]/20',
    glow: 'shadow-[hsl(var(--success))]/10',
    gradient: 'from-[hsl(var(--success))]/20 to-transparent',
  },
  warning: {
    bg: 'bg-[hsl(var(--warning))]/10',
    text: 'text-[hsl(var(--warning))]',
    border: 'border-[hsl(var(--warning))]/20',
    glow: 'shadow-[hsl(var(--warning))]/10',
    gradient: 'from-[hsl(var(--warning))]/20 to-transparent',
  },
  info: {
    bg: 'bg-[hsl(var(--info))]/10',
    text: 'text-[hsl(var(--info))]',
    border: 'border-[hsl(var(--info))]/20',
    glow: 'shadow-[hsl(var(--info))]/10',
    gradient: 'from-[hsl(var(--info))]/20 to-transparent',
  },
}

function KPICard({ title, value, subtitle, icon, accentColor, footer, trend }: KPICardProps) {
  const colors = accentColors[accentColor]

  return (
    <div className={cn(
      'group relative overflow-hidden rounded-xl',
      'bg-[hsl(var(--card))] border border-[hsl(var(--border))]',
      'transition-all duration-300',
      'hover:border-[hsl(var(--border))]/80',
      'hover:shadow-lg',
      colors.glow
    )}>
      {/* Gradient Overlay */}
      <div className={cn(
        'absolute inset-0 opacity-0 group-hover:opacity-100',
        'bg-gradient-to-br transition-opacity duration-500',
        colors.gradient
      )} />

      {/* Corner Accent */}
      <div className={cn(
        'absolute top-0 right-0 w-24 h-24',
        'bg-gradient-to-bl opacity-5',
        colors.gradient
      )} />

      <div className="relative p-5">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className={cn(
            'p-2.5 rounded-lg border',
            colors.bg,
            colors.border
          )}>
            <div className={colors.text}>{icon}</div>
          </div>

          {trend && (
            <div className={cn(
              'flex items-center gap-1 px-2 py-1 rounded-md text-xs font-mono',
              trend.value >= 0
                ? 'bg-[hsl(var(--success))]/10 text-[hsl(var(--success))]'
                : 'bg-[hsl(var(--destructive))]/10 text-[hsl(var(--destructive))]'
            )}>
              <TrendingUp className={cn('w-3 h-3', trend.value < 0 && 'rotate-180')} />
              <span>{trend.value >= 0 ? '+' : ''}{trend.value}%</span>
            </div>
          )}
        </div>

        {/* Title */}
        <p className="text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wider mb-1">
          {title}
        </p>

        {/* Value */}
        <div className="flex items-baseline gap-1.5 mb-3">
          <span className={cn(
            'text-3xl font-bold font-mono tracking-tight',
            'text-[hsl(var(--foreground))]'
          )}>
            {value}
          </span>
          {subtitle && (
            <span className="text-sm text-[hsl(var(--muted-foreground))] font-mono">
              {subtitle}
            </span>
          )}
        </div>

        {/* Footer */}
        {footer && (
          <div className="pt-3 border-t border-[hsl(var(--border))]">
            {footer}
          </div>
        )}
      </div>

      {/* Bottom Accent Line */}
      <div className={cn(
        'absolute bottom-0 left-0 right-0 h-0.5',
        'opacity-0 group-hover:opacity-100',
        'transition-opacity duration-300',
        colors.bg.replace('/10', '')
      )} />
    </div>
  )
}

export function KPIDashboard() {
  const agents = useAllAgents()
  const tasks = useTaskStore((state) => state.tasks)
  const { approvalQueue } = useTicketStore()

  const kpis = useMemo(() => {
    const activeAgents = agents.filter((a) => a.isActive).length
    const totalAgents = agents.length

    const pendingTasks = tasks.filter((t) => t.status === 'pending').length
    const inProgressTasks = tasks.filter((t) => t.status === 'in_progress').length
    const completedTasks = tasks.filter((t) => t.status === 'completed').length
    const totalTasks = tasks.length

    const pendingApprovals = approvalQueue.length

    const completionRate = totalTasks > 0 ? ((completedTasks / totalTasks) * 100).toFixed(1) : '0'

    return {
      activeAgents,
      totalAgents,
      pendingTasks,
      inProgressTasks,
      completedTasks,
      totalTasks,
      pendingApprovals,
      completionRate,
    }
  }, [agents, tasks, approvalQueue])

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {/* Active Agents KPI */}
      <KPICard
        title="Active Agents"
        value={kpis.activeAgents}
        subtitle={`/ ${kpis.totalAgents}`}
        icon={<Users className="w-5 h-5" />}
        accentColor="info"
        footer={
          <div className="flex items-center gap-2">
            <div className="flex -space-x-1">
              {[...Array(Math.min(kpis.activeAgents, 3))].map((_, i) => (
                <div
                  key={i}
                  className="w-5 h-5 rounded-full bg-[hsl(var(--info))]/20 border-2 border-[hsl(var(--card))] flex items-center justify-center"
                >
                  <Activity className="w-2.5 h-2.5 text-[hsl(var(--info))]" />
                </div>
              ))}
            </div>
            <span className="text-xs text-[hsl(var(--muted-foreground))]">
              {kpis.activeAgents > 0 ? 'Running' : 'No active agents'}
            </span>
          </div>
        }
      />

      {/* Tasks KPI */}
      <KPICard
        title="In Progress"
        value={kpis.inProgressTasks}
        subtitle={`/ ${kpis.totalTasks}`}
        icon={<ListTodo className="w-5 h-5" />}
        accentColor="success"
        footer={
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-[hsl(var(--warning))]" />
              <span className="text-xs font-mono text-[hsl(var(--warning))]">
                {kpis.pendingTasks}
              </span>
              <span className="text-xs text-[hsl(var(--muted-foreground))]">pending</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-[hsl(var(--success))]" />
              <span className="text-xs font-mono text-[hsl(var(--success))]">
                {kpis.completedTasks}
              </span>
              <span className="text-xs text-[hsl(var(--muted-foreground))]">done</span>
            </div>
          </div>
        }
      />

      {/* Completion Rate KPI */}
      <KPICard
        title="Completion Rate"
        value={`${kpis.completionRate}%`}
        icon={<Zap className="w-5 h-5" />}
        accentColor="primary"
        footer={
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-[hsl(var(--muted-foreground))]">Progress</span>
              <span className="font-mono text-[hsl(var(--foreground))]">{kpis.completionRate}%</span>
            </div>
            <div className="relative h-1.5 bg-[hsl(var(--muted))] rounded-full overflow-hidden">
              <div
                className={cn(
                  'absolute inset-y-0 left-0 rounded-full',
                  'bg-gradient-to-r from-[hsl(var(--primary))] to-[hsl(var(--accent))]',
                  'transition-all duration-700 ease-out'
                )}
                style={{ width: `${kpis.completionRate}%` }}
              />
              {/* Shimmer effect */}
              <div
                className="absolute inset-y-0 left-0 w-full bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full animate-shimmer"
                style={{ width: `${kpis.completionRate}%` }}
              />
            </div>
          </div>
        }
      />

      {/* Pending Approvals KPI */}
      <KPICard
        title="Pending Approvals"
        value={kpis.pendingApprovals}
        icon={<Clock className="w-5 h-5" />}
        accentColor="warning"
        footer={
          kpis.pendingApprovals > 0 ? (
            <div className="flex items-center gap-2">
              <div className="relative">
                <div className="w-2 h-2 rounded-full bg-[hsl(var(--warning))]" />
                <div className="absolute inset-0 w-2 h-2 rounded-full bg-[hsl(var(--warning))] animate-ping" />
              </div>
              <span className="text-xs text-[hsl(var(--warning))]">
                Action required
              </span>
            </div>
          ) : (
            <span className="text-xs text-[hsl(var(--muted-foreground))]">
              All approvals completed
            </span>
          )
        }
      />
    </div>
  )
}
