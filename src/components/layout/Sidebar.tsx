/**
 * Sidebar - Terminal Elegance 디자인의 접이식 사이드바
 */

import { useState, useCallback, type ReactNode } from 'react'
import { cn } from '@/lib/utils'
import {
  LayoutDashboard,
  ListTodo,
  User,
  Settings,
  ChevronLeft,
  ChevronRight,
  Terminal,
} from 'lucide-react'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '../ui/tooltip'

export type TabType = 'dashboard' | 'tasks' | 'personalization' | 'settings'

interface NavItem {
  id: TabType
  label: string
  icon: ReactNode
  badge?: number
}

interface SidebarProps {
  activeTab: TabType
  onTabChange: (tab: TabType) => void
  pendingApprovals?: number
  pendingTasks?: number
}

const NAV_ITEMS: NavItem[] = [
  {
    id: 'tasks',
    label: 'Tasks',
    icon: <ListTodo className="h-5 w-5" />,
  },
  {
    id: 'dashboard',
    label: 'Dashboard',
    icon: <LayoutDashboard className="h-5 w-5" />,
  },
]

const NAV_SECONDARY: NavItem[] = [
  {
    id: 'personalization',
    label: 'Personalization',
    icon: <User className="h-5 w-5" />,
  },
  {
    id: 'settings',
    label: 'Settings',
    icon: <Settings className="h-5 w-5" />,
  },
]

export function Sidebar({
  activeTab,
  onTabChange,
  pendingApprovals = 0,
  pendingTasks = 0,
}: SidebarProps) {
  const [isCollapsed, setIsCollapsed] = useState(false)

  const toggleCollapse = useCallback(() => {
    setIsCollapsed((prev) => !prev)
  }, [])

  // 배지 카운트 추가
  const navItemsWithBadges = NAV_ITEMS.map((item) => ({
    ...item,
    badge: item.id === 'tasks' ? pendingTasks : item.id === 'dashboard' ? pendingApprovals : undefined,
  }))

  return (
    <TooltipProvider delayDuration={0}>
      <aside
        className={cn(
          'hidden md:flex flex-col h-full relative',
          'bg-[hsl(var(--sidebar-background))]',
          'border-r border-[hsl(var(--sidebar-border))]',
          'transition-all duration-300 ease-out',
          isCollapsed ? 'w-16' : 'w-60'
        )}
      >
        {/* Glow Effect */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-20 -left-20 w-40 h-40 bg-[hsl(var(--primary))] opacity-5 blur-3xl" />
          <div className="absolute -bottom-20 -left-10 w-32 h-32 bg-[hsl(var(--accent))] opacity-5 blur-3xl" />
        </div>

        {/* Logo */}
        <div className={cn(
          'relative flex items-center h-16 px-4',
          'border-b border-[hsl(var(--sidebar-border))]',
          isCollapsed ? 'justify-center' : 'justify-between'
        )}>
          <div className="flex items-center gap-3">
            <div className="relative group">
              <div className="absolute inset-0 bg-[hsl(var(--primary))] opacity-20 blur-md rounded-lg group-hover:opacity-40 transition-opacity" />
              <div className={cn(
                'relative w-9 h-9 rounded-lg flex items-center justify-center',
                'bg-gradient-to-br from-[hsl(var(--primary))] to-[hsl(var(--accent))]',
                'shadow-lg shadow-[hsl(var(--primary))]/20'
              )}>
                <Terminal className="w-5 h-5 text-[hsl(var(--background))]" />
              </div>
            </div>
            {!isCollapsed && (
              <div className="flex flex-col">
                <span className="font-semibold text-[hsl(var(--sidebar-foreground))] text-sm tracking-tight">
                  Agent Monitor
                </span>
                <span className="text-[10px] text-[hsl(var(--muted-foreground))] font-mono tracking-wider">
                  v2.0
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Main Navigation */}
        <nav className="flex-1 p-3 space-y-1 relative" aria-label="Main navigation">
          {/* Section Label */}
          {!isCollapsed && (
            <div className="px-3 py-2">
              <span className="text-[10px] font-mono uppercase tracking-widest text-[hsl(var(--muted-foreground))]">
                Navigation
              </span>
            </div>
          )}

          <div className="space-y-1">
            {navItemsWithBadges.map((item) => (
              <NavButton
                key={item.id}
                item={item}
                isActive={activeTab === item.id}
                isCollapsed={isCollapsed}
                onClick={() => onTabChange(item.id)}
              />
            ))}
          </div>

          {/* Divider */}
          <div className="my-4 mx-3">
            <div className="h-px bg-gradient-to-r from-transparent via-[hsl(var(--sidebar-border))] to-transparent" />
          </div>

          {/* Section Label */}
          {!isCollapsed && (
            <div className="px-3 py-2">
              <span className="text-[10px] font-mono uppercase tracking-widest text-[hsl(var(--muted-foreground))]">
                System
              </span>
            </div>
          )}

          <div className="space-y-1">
            {NAV_SECONDARY.map((item) => (
              <NavButton
                key={item.id}
                item={item}
                isActive={activeTab === item.id}
                isCollapsed={isCollapsed}
                onClick={() => onTabChange(item.id)}
              />
            ))}
          </div>
        </nav>

        {/* Collapse Button */}
        <div className="p-3 border-t border-[hsl(var(--sidebar-border))]">
          <button
            onClick={toggleCollapse}
            className={cn(
              'w-full flex items-center gap-2 px-3 py-2 rounded-lg',
              'text-sm text-[hsl(var(--muted-foreground))]',
              'hover:text-[hsl(var(--sidebar-foreground))]',
              'hover:bg-[hsl(var(--sidebar-accent))]',
              'transition-all duration-200',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--ring))]',
              isCollapsed && 'justify-center'
            )}
            aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {isCollapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <>
                <ChevronLeft className="h-4 w-4" />
                <span className="font-medium">Collapse</span>
              </>
            )}
          </button>
        </div>

        {/* Status Indicator */}
        <div className={cn(
          'px-3 pb-3',
          isCollapsed && 'flex justify-center'
        )}>
          <div className={cn(
            'flex items-center gap-2 px-3 py-2 rounded-lg',
            'bg-[hsl(var(--success))]/5 border border-[hsl(var(--success))]/20',
            isCollapsed && 'px-2'
          )}>
            <div className="relative">
              <div className="w-2 h-2 rounded-full bg-[hsl(var(--success))]" />
              <div className="absolute inset-0 w-2 h-2 rounded-full bg-[hsl(var(--success))] animate-ping opacity-75" />
            </div>
            {!isCollapsed && (
              <span className="text-xs text-[hsl(var(--success))] font-medium">
                System Online
              </span>
            )}
          </div>
        </div>
      </aside>
    </TooltipProvider>
  )
}

interface NavButtonProps {
  item: NavItem
  isActive: boolean
  isCollapsed: boolean
  onClick: () => void
}

function NavButton({ item, isActive, isCollapsed, onClick }: NavButtonProps) {
  const button = (
    <button
      onClick={onClick}
      className={cn(
        'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg',
        'text-sm font-medium transition-all duration-200',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--ring))]',
        isActive
          ? cn(
              'bg-[hsl(var(--sidebar-accent))]',
              'text-[hsl(var(--primary))]',
              'shadow-sm shadow-[hsl(var(--primary))]/10',
              'border border-[hsl(var(--primary))]/20'
            )
          : cn(
              'text-[hsl(var(--muted-foreground))]',
              'hover:bg-[hsl(var(--sidebar-accent))]',
              'hover:text-[hsl(var(--sidebar-foreground))]',
              'border border-transparent'
            ),
        isCollapsed && 'justify-center px-0'
      )}
      aria-current={isActive ? 'page' : undefined}
    >
      <span className={cn(
        'transition-colors duration-200',
        isActive && 'text-[hsl(var(--primary))]'
      )}>
        {item.icon}
      </span>
      {!isCollapsed && (
        <>
          <span className="flex-1 text-left">{item.label}</span>
          {item.badge !== undefined && item.badge > 0 && (
            <span className={cn(
              'min-w-5 h-5 px-1.5 rounded-md',
              'bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))]',
              'text-xs font-mono font-semibold',
              'flex items-center justify-center',
              'border border-[hsl(var(--primary))]/20'
            )}>
              {item.badge > 99 ? '99+' : item.badge}
            </span>
          )}
        </>
      )}
    </button>
  )

  if (isCollapsed) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>
          <div className="relative">
            {button}
            {item.badge !== undefined && item.badge > 0 && (
              <span className={cn(
                'absolute -top-1 -right-1 min-w-4 h-4 px-1',
                'rounded-full bg-[hsl(var(--primary))]',
                'text-[hsl(var(--primary-foreground))]',
                'text-[10px] font-mono font-semibold',
                'flex items-center justify-center',
                'shadow-lg shadow-[hsl(var(--primary))]/30'
              )}>
                {item.badge > 9 ? '9+' : item.badge}
              </span>
            )}
          </div>
        </TooltipTrigger>
        <TooltipContent side="right" className="flex items-center gap-2">
          {item.label}
          {item.badge !== undefined && item.badge > 0 && (
            <span className="min-w-5 h-5 px-1.5 rounded-md bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))] text-xs font-mono flex items-center justify-center">
              {item.badge}
            </span>
          )}
        </TooltipContent>
      </Tooltip>
    )
  }

  return button
}

export default Sidebar
