/**
 * DashboardLayout - 프로페셔널 대시보드 레이아웃
 *
 * Features:
 * - 사이드바 네비게이션 (접이식)
 * - 반응형 디자인 (모바일/태블릿/데스크톱)
 * - 라이트/다크 테마 지원
 * - 접근성 (ARIA, 키보드 네비게이션)
 */

import { useState, useCallback, useEffect, type ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { Sidebar, type TabType } from './Sidebar'
import { Header } from './Header'
import { IconButton } from '../ui/Button'
import { X } from 'lucide-react'

export type { TabType }

interface DashboardLayoutProps {
  children: ReactNode
  activeTab: TabType
  onTabChange: (tab: TabType) => void
  rightPanel?: ReactNode
  pendingApprovals?: number
  pendingTasks?: number
}

// Mobile Navigation Items
const MOBILE_NAV_ITEMS = [
  { id: 'tasks' as TabType, label: 'Tasks', icon: '📋' },
  { id: 'dashboard' as TabType, label: 'Dashboard', icon: '📊' },
  { id: 'personalization' as TabType, label: 'Profile', icon: '👤' },
  { id: 'settings' as TabType, label: 'Settings', icon: '⚙️' },
]

export function DashboardLayout({
  children,
  activeTab,
  onTabChange,
  rightPanel,
  pendingApprovals = 0,
  pendingTasks = 0,
}: DashboardLayoutProps) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
  const [isRightPanelOpen, setIsRightPanelOpen] = useState(false)

  // 모바일 메뉴 토글
  const toggleMobileMenu = useCallback(() => {
    setIsMobileMenuOpen((prev) => !prev)
  }, [])

  // 오른쪽 패널 토글 (모바일)
  const toggleRightPanel = useCallback(() => {
    setIsRightPanelOpen((prev) => !prev)
  }, [])

  // 탭 변경 시 모바일 메뉴 닫기
  const handleTabChange = useCallback(
    (tab: TabType) => {
      onTabChange(tab)
      setIsMobileMenuOpen(false)
    },
    [onTabChange]
  )

  // ESC 키로 메뉴 닫기
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsMobileMenuOpen(false)
        setIsRightPanelOpen(false)
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [])

  // 모바일 메뉴 열릴 때 스크롤 방지
  useEffect(() => {
    if (isMobileMenuOpen || isRightPanelOpen) {
      document.body.classList.add('mobile-nav-open')
    } else {
      document.body.classList.remove('mobile-nav-open')
    }

    return () => {
      document.body.classList.remove('mobile-nav-open')
    }
  }, [isMobileMenuOpen, isRightPanelOpen])

  // Page title based on active tab
  const pageTitle = {
    tasks: 'Tasks',
    dashboard: 'Dashboard',
    personalization: 'Personalization',
    settings: 'Settings',
  }[activeTab]

  return (
    <div className="h-screen bg-[hsl(var(--background))] flex overflow-hidden">
      {/* Skip Navigation Link */}
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>

      {/* Desktop Sidebar */}
      <Sidebar
        activeTab={activeTab}
        onTabChange={onTabChange}
        pendingApprovals={pendingApprovals}
        pendingTasks={pendingTasks}
      />

      {/* Mobile Navigation Overlay */}
      {isMobileMenuOpen && (
        <div
          className="md:hidden fixed inset-0 bg-black/60 z-40 animate-fade-in backdrop-blur-sm"
          onClick={() => setIsMobileMenuOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Mobile Navigation Menu */}
      <nav
        id="mobile-nav"
        className={cn(
          'md:hidden fixed left-0 top-0 bottom-0 w-72 bg-[hsl(var(--card))] z-50',
          'transform transition-transform duration-300 ease-in-out',
          'safe-area-top safe-area-bottom border-r border-[hsl(var(--border))]',
          isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full'
        )}
        aria-label="Main navigation"
        role="navigation"
      >
        {/* Mobile Nav Header */}
        <div className="p-4 border-b border-[hsl(var(--border))] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-[hsl(var(--primary))] rounded-lg flex items-center justify-center">
              <span className="text-[hsl(var(--primary-foreground))] font-bold text-sm">AM</span>
            </div>
            <span className="font-semibold text-[hsl(var(--foreground))]">Agent Monitor</span>
          </div>
          <IconButton
            icon={<X className="h-5 w-5" />}
            aria-label="Close menu"
            variant="ghost"
            size="sm"
            onClick={() => setIsMobileMenuOpen(false)}
          />
        </div>

        {/* Mobile Nav Items */}
        <ul className="p-3 space-y-1" role="menubar">
          {MOBILE_NAV_ITEMS.map((item) => (
            <li key={item.id} role="none">
              <button
                onClick={() => handleTabChange(item.id)}
                className={cn(
                  'w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors text-sm font-medium',
                  activeTab === item.id
                    ? 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]'
                    : 'text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--accent))] hover:text-[hsl(var(--accent-foreground))]'
                )}
                role="menuitem"
                aria-current={activeTab === item.id ? 'page' : undefined}
              >
                <span className="text-lg">{item.icon}</span>
                <span>{item.label}</span>
              </button>
            </li>
          ))}
        </ul>
      </nav>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Header */}
        <Header
          title={pageTitle}
          onMobileMenuToggle={toggleMobileMenu}
          onChatPanelToggle={toggleRightPanel}
          isMobileMenuOpen={isMobileMenuOpen}
          isChatPanelOpen={isRightPanelOpen}
          showChatButton={Boolean(rightPanel)}
        />

        {/* Content + Right Panel Container */}
        <div className="flex-1 flex overflow-hidden">
          {/* Main Content */}
          <main
            id="main-content"
            className="flex-1 overflow-auto p-4 md:p-6"
            role="main"
            aria-label="Main content"
            tabIndex={-1}
          >
            {children}
          </main>

          {/* Right Panel - Desktop */}
          {rightPanel && (
            <aside
              className="hidden md:flex w-80 lg:w-96 border-l border-[hsl(var(--border))] bg-[hsl(var(--card))] flex-col flex-shrink-0 h-full overflow-hidden"
              aria-label="Chat panel"
            >
              {rightPanel}
            </aside>
          )}
        </div>

        {/* Mobile Bottom Navigation */}
        <nav
          className="md:hidden bg-[hsl(var(--card))] border-t border-[hsl(var(--border))] flex-shrink-0 safe-area-bottom"
          aria-label="Quick navigation"
        >
          <ul className="flex" role="tablist">
            {MOBILE_NAV_ITEMS.map((item) => (
              <li key={item.id} role="presentation" className="flex-1">
                <button
                  onClick={() => onTabChange(item.id)}
                  className={cn(
                    'w-full flex flex-col items-center gap-1 py-2 px-1 transition-colors',
                    activeTab === item.id
                      ? 'text-[hsl(var(--primary))]'
                      : 'text-[hsl(var(--muted-foreground))]'
                  )}
                  role="tab"
                  aria-selected={activeTab === item.id}
                  aria-label={item.label}
                >
                  <span className="text-lg">{item.icon}</span>
                  <span className="text-[10px] font-medium">{item.label}</span>
                </button>
              </li>
            ))}
          </ul>
        </nav>
      </div>

      {/* Right Panel - Mobile Overlay */}
      {rightPanel && isRightPanelOpen && (
        <>
          <div
            className="md:hidden fixed inset-0 bg-black/60 z-40 animate-fade-in backdrop-blur-sm"
            onClick={() => setIsRightPanelOpen(false)}
            aria-hidden="true"
          />
          <aside
            className="md:hidden fixed right-0 top-0 bottom-0 w-[85%] max-w-md bg-[hsl(var(--card))] z-50 animate-slide-in flex flex-col safe-area-top safe-area-bottom"
            aria-label="Chat panel"
          >
            <div className="p-3 border-b border-[hsl(var(--border))] flex items-center justify-between">
              <span className="font-medium text-[hsl(var(--foreground))]">Chat</span>
              <IconButton
                icon={<X className="h-5 w-5" />}
                aria-label="Close panel"
                variant="ghost"
                size="sm"
                onClick={() => setIsRightPanelOpen(false)}
              />
            </div>
            <div className="flex-1 overflow-hidden">{rightPanel}</div>
          </aside>
        </>
      )}
    </div>
  )
}

export default DashboardLayout
