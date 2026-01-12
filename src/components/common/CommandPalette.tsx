/**
 * CommandPalette - 전역 명령 팔레트 (Cmd+K)
 */

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import { cn } from '@/lib/utils'
import { useTaskStore } from '@/stores/taskStore'
import { useAllAgents } from '@/hooks/useAllAgents'
import {
  Search,
  ListTodo,
  Bot,
  Plus,
  Settings,
  User,
  LayoutDashboard,
  ArrowRight,
  Command,
  Hash,
} from 'lucide-react'

type CommandCategory = 'navigation' | 'actions' | 'tasks' | 'agents'

interface CommandItem {
  id: string
  label: string
  description?: string
  category: CommandCategory
  icon: React.ReactNode
  action: () => void
  keywords?: string[]
}

type TabType = 'dashboard' | 'tasks' | 'personalization' | 'settings'

interface CommandPaletteProps {
  isOpen: boolean
  onClose: () => void
  onNavigate: (tab: TabType) => void
  onCreateTask: () => void
  onCreateAgent: () => void
  onSelectTask?: (taskId: string) => void
  onSelectAgent?: (agentId: string) => void
}

const CATEGORY_LABELS: Record<CommandCategory, string> = {
  navigation: 'Navigation',
  actions: 'Actions',
  tasks: 'Tasks',
  agents: 'Agents',
}

const CATEGORY_ORDER: CommandCategory[] = ['actions', 'navigation', 'tasks', 'agents']

export function CommandPalette({
  isOpen,
  onClose,
  onNavigate,
  onCreateTask,
  onCreateAgent,
  onSelectTask,
  onSelectAgent,
}: CommandPaletteProps) {
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLDivElement>(null)

  const tasks = useTaskStore((state) => state.tasks)
  const agents = useAllAgents()

  // 기본 명령어 목록
  const baseCommands: CommandItem[] = useMemo(
    () => [
      // Actions
      {
        id: 'new-task',
        label: 'Create New Task',
        description: 'Create a new task',
        category: 'actions',
        icon: <Plus className="w-4 h-4" />,
        action: () => {
          onCreateTask()
          onClose()
        },
        keywords: ['new', 'add', 'create', 'task'],
      },
      {
        id: 'new-agent',
        label: 'Create New Agent',
        description: 'Create a custom agent',
        category: 'actions',
        icon: <Plus className="w-4 h-4" />,
        action: () => {
          onCreateAgent()
          onClose()
        },
        keywords: ['new', 'add', 'create', 'agent'],
      },
      // Navigation
      {
        id: 'nav-tasks',
        label: 'Go to Tasks',
        description: 'View and manage tasks',
        category: 'navigation',
        icon: <ListTodo className="w-4 h-4" />,
        action: () => {
          onNavigate('tasks')
          onClose()
        },
        keywords: ['tasks', 'list', 'todo'],
      },
      {
        id: 'nav-dashboard',
        label: 'Go to Dashboard',
        description: 'View dashboard and KPIs',
        category: 'navigation',
        icon: <LayoutDashboard className="w-4 h-4" />,
        action: () => {
          onNavigate('dashboard')
          onClose()
        },
        keywords: ['dashboard', 'home', 'overview', 'kpi'],
      },
      {
        id: 'nav-personalization',
        label: 'Go to Personalization',
        description: 'Customize your preferences',
        category: 'navigation',
        icon: <User className="w-4 h-4" />,
        action: () => {
          onNavigate('personalization')
          onClose()
        },
        keywords: ['personalization', 'preferences', 'profile'],
      },
      {
        id: 'nav-settings',
        label: 'Go to Settings',
        description: 'Configure application settings',
        category: 'navigation',
        icon: <Settings className="w-4 h-4" />,
        action: () => {
          onNavigate('settings')
          onClose()
        },
        keywords: ['settings', 'config', 'options'],
      },
    ],
    [onClose, onCreateAgent, onCreateTask, onNavigate]
  )

  // 태스크 명령어 (최근 10개)
  const taskCommands: CommandItem[] = useMemo(
    () =>
      tasks.slice(0, 10).map((task) => ({
        id: `task-${task.id}`,
        label: task.title,
        description: `${task.status} • ${task.priority}`,
        category: 'tasks' as CommandCategory,
        icon: <Hash className="w-4 h-4" />,
        action: () => {
          onSelectTask?.(task.id)
          onNavigate('tasks')
          onClose()
        },
        keywords: [task.title, task.status, task.priority, ...task.tags],
      })),
    [tasks, onSelectTask, onNavigate, onClose]
  )

  // 에이전트 명령어
  const agentCommands: CommandItem[] = useMemo(
    () =>
      agents.slice(0, 10).map((agent) => ({
        id: `agent-${agent.id}`,
        label: agent.name,
        description: agent.type,
        category: 'agents' as CommandCategory,
        icon: <Bot className="w-4 h-4" />,
        action: () => {
          onSelectAgent?.(agent.id)
          onNavigate('dashboard')
          onClose()
        },
        keywords: [agent.name, agent.type],
      })),
    [agents, onSelectAgent, onNavigate, onClose]
  )

  // 전체 명령어 목록
  const allCommands = useMemo(
    () => [...baseCommands, ...taskCommands, ...agentCommands],
    [baseCommands, taskCommands, agentCommands]
  )

  // 검색 필터링
  const filteredCommands = useMemo(() => {
    if (!query.trim()) {
      // 검색어 없으면 기본 명령어만
      return baseCommands
    }

    const lowerQuery = query.toLowerCase()
    return allCommands.filter((cmd) => {
      const labelMatch = cmd.label.toLowerCase().includes(lowerQuery)
      const descMatch = cmd.description?.toLowerCase().includes(lowerQuery)
      const keywordMatch = cmd.keywords?.some((kw) => kw.toLowerCase().includes(lowerQuery))
      return labelMatch || descMatch || keywordMatch
    })
  }, [query, allCommands, baseCommands])

  // 카테고리별 그룹화
  const groupedCommands = useMemo(() => {
    const groups: Record<CommandCategory, CommandItem[]> = {
      navigation: [],
      actions: [],
      tasks: [],
      agents: [],
    }

    filteredCommands.forEach((cmd) => {
      groups[cmd.category].push(cmd)
    })

    return CATEGORY_ORDER.filter((cat) => groups[cat].length > 0).map((cat) => ({
      category: cat,
      label: CATEGORY_LABELS[cat],
      items: groups[cat],
    }))
  }, [filteredCommands])

  // 평탄화된 목록 (키보드 네비게이션용)
  const flatItems = useMemo(
    () => groupedCommands.flatMap((g) => g.items),
    [groupedCommands]
  )

  // 선택 인덱스 리셋
  useEffect(() => {
    setSelectedIndex(0)
  }, [query])

  // 열릴 때 초기화
  useEffect(() => {
    if (isOpen) {
      setQuery('')
      setSelectedIndex(0)
      setTimeout(() => inputRef.current?.focus(), 0)
    }
  }, [isOpen])

  // 선택 항목 스크롤
  useEffect(() => {
    const selectedItem = listRef.current?.querySelector('[data-selected="true"]')
    selectedItem?.scrollIntoView({ block: 'nearest' })
  }, [selectedIndex])

  // 키보드 네비게이션
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault()
          setSelectedIndex((i) => (i + 1) % flatItems.length)
          break
        case 'ArrowUp':
          e.preventDefault()
          setSelectedIndex((i) => (i - 1 + flatItems.length) % flatItems.length)
          break
        case 'Enter':
          e.preventDefault()
          flatItems[selectedIndex]?.action()
          break
        case 'Escape':
          e.preventDefault()
          onClose()
          break
      }
    },
    [flatItems, selectedIndex, onClose]
  )

  return (
    <Dialog.Root open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay
          className={cn(
            'fixed inset-0 z-50',
            'bg-black/60 backdrop-blur-sm',
            'data-[state=open]:animate-in data-[state=closed]:animate-out',
            'data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0'
          )}
        />
        <Dialog.Content
          className={cn(
            'fixed left-1/2 top-[20%] z-50 w-full max-w-lg -translate-x-1/2',
            'data-[state=open]:animate-in data-[state=closed]:animate-out',
            'data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0',
            'data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95',
            'data-[state=closed]:slide-out-to-left-1/2 data-[state=open]:slide-in-from-left-1/2',
            'duration-200'
          )}
          onKeyDown={handleKeyDown}
        >
          <div
            className={cn(
              'overflow-hidden rounded-xl',
              'bg-[hsl(var(--card))] border border-[hsl(var(--border))]',
              'shadow-2xl shadow-black/20'
            )}
          >
            {/* Search Input */}
            <div className="flex items-center gap-3 px-4 border-b border-[hsl(var(--border))]">
              <Search className="w-5 h-5 text-[hsl(var(--muted-foreground))]" />
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search commands, tasks, agents..."
                className={cn(
                  'flex-1 h-14 bg-transparent',
                  'text-[hsl(var(--foreground))] placeholder:text-[hsl(var(--muted-foreground))]',
                  'focus:outline-none',
                  'text-sm'
                )}
              />
              <kbd
                className={cn(
                  'hidden sm:inline-flex items-center gap-1',
                  'px-2 py-1 rounded',
                  'bg-[hsl(var(--muted))] text-[hsl(var(--muted-foreground))]',
                  'text-xs font-mono'
                )}
              >
                ESC
              </kbd>
            </div>

            {/* Results List */}
            <div ref={listRef} className="max-h-80 overflow-y-auto p-2">
              {groupedCommands.length === 0 ? (
                <div className="py-8 text-center text-sm text-[hsl(var(--muted-foreground))]">
                  No results found for "{query}"
                </div>
              ) : (
                groupedCommands.map((group) => (
                  <div key={group.category} className="mb-2 last:mb-0">
                    <div className="px-2 py-1.5 text-xs font-medium text-[hsl(var(--muted-foreground))] uppercase tracking-wider">
                      {group.label}
                    </div>
                    {group.items.map((item) => {
                      const index = flatItems.indexOf(item)
                      const isSelected = index === selectedIndex

                      return (
                        <button
                          key={item.id}
                          data-selected={isSelected}
                          onClick={item.action}
                          onMouseEnter={() => setSelectedIndex(index)}
                          className={cn(
                            'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg',
                            'text-left transition-colors',
                            isSelected
                              ? 'bg-[hsl(var(--accent))] text-[hsl(var(--accent-foreground))]'
                              : 'text-[hsl(var(--foreground))] hover:bg-[hsl(var(--muted))]'
                          )}
                        >
                          <span
                            className={cn(
                              'flex-shrink-0',
                              isSelected
                                ? 'text-[hsl(var(--primary))]'
                                : 'text-[hsl(var(--muted-foreground))]'
                            )}
                          >
                            {item.icon}
                          </span>
                          <div className="flex-1 min-w-0">
                            <div className="text-sm font-medium truncate">{item.label}</div>
                            {item.description && (
                              <div className="text-xs text-[hsl(var(--muted-foreground))] truncate">
                                {item.description}
                              </div>
                            )}
                          </div>
                          {isSelected && (
                            <ArrowRight className="w-4 h-4 text-[hsl(var(--muted-foreground))]" />
                          )}
                        </button>
                      )
                    })}
                  </div>
                ))
              )}
            </div>

            {/* Footer */}
            <div
              className={cn(
                'flex items-center justify-between px-4 py-2',
                'border-t border-[hsl(var(--border))]',
                'bg-[hsl(var(--muted))]/30',
                'text-xs text-[hsl(var(--muted-foreground))]'
              )}
            >
              <div className="flex items-center gap-4">
                <span className="flex items-center gap-1">
                  <kbd className="px-1.5 py-0.5 rounded bg-[hsl(var(--muted))] font-mono">↑↓</kbd>
                  Navigate
                </span>
                <span className="flex items-center gap-1">
                  <kbd className="px-1.5 py-0.5 rounded bg-[hsl(var(--muted))] font-mono">↵</kbd>
                  Select
                </span>
              </div>
              <div className="flex items-center gap-1">
                <Command className="w-3 h-3" />
                <span>K to open</span>
              </div>
            </div>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}

export default CommandPalette
