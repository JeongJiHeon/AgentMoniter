/**
 * Header - Terminal Elegance 디자인의 상단 헤더
 */

import { useState, useEffect } from 'react'
import { cn } from '@/lib/utils'
import { useTheme } from '@/hooks/useTheme'
import { useWebSocketStore } from '@/stores/websocketStore'
import { Button } from '../ui/Button'
import {
  Sun,
  Moon,
  Menu,
  MessageSquare,
  Wifi,
  WifiOff,
  X,
  Activity,
  Terminal,
  RefreshCw,
  Loader2,
} from 'lucide-react'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '../ui/tooltip'

interface HeaderProps {
  title?: string
  onMobileMenuToggle?: () => void
  onChatPanelToggle?: () => void
  isMobileMenuOpen?: boolean
  isChatPanelOpen?: boolean
  showMobileMenuButton?: boolean
  showChatButton?: boolean
  onManualReconnect?: () => void
}

export function Header({
  title,
  onMobileMenuToggle,
  onChatPanelToggle,
  isMobileMenuOpen = false,
  isChatPanelOpen = false,
  showMobileMenuButton = true,
  showChatButton = true,
  onManualReconnect,
}: HeaderProps) {
  // Use websocket store for detailed connection state
  const {
    connectionState,
    reconnectAttempts,
    maxReconnectAttempts,
    lastError,
    resetReconnectAttempts,
  } = useWebSocketStore()
  const { resolvedTheme, toggleTheme } = useTheme()
  const [currentTime, setCurrentTime] = useState(new Date())

  // 시간 업데이트
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date())
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    })
  }

  return (
    <TooltipProvider>
      <header className={cn(
        'h-14 flex items-center justify-between px-4 flex-shrink-0 relative',
        'bg-[hsl(var(--card))]/80 backdrop-blur-sm',
        'border-b border-[hsl(var(--border))]'
      )}>
        {/* Subtle gradient overlay */}
        <div className="absolute inset-0 bg-gradient-to-r from-[hsl(var(--primary))]/5 via-transparent to-[hsl(var(--accent))]/5 pointer-events-none" />

        {/* Left Section */}
        <div className="flex items-center gap-4 relative z-10">
          {/* Mobile Menu Button */}
          {showMobileMenuButton && (
            <Button
              variant="ghost"
              size="icon"
              className="md:hidden"
              onClick={onMobileMenuToggle}
              aria-label={isMobileMenuOpen ? 'Close menu' : 'Open menu'}
              aria-expanded={isMobileMenuOpen}
            >
              {isMobileMenuOpen ? (
                <X className="h-5 w-5" />
              ) : (
                <Menu className="h-5 w-5" />
              )}
            </Button>
          )}

          {/* Mobile Logo */}
          <div className="flex items-center gap-2 md:hidden">
            <div className={cn(
              'w-8 h-8 rounded-lg flex items-center justify-center',
              'bg-gradient-to-br from-[hsl(var(--primary))] to-[hsl(var(--accent))]',
              'shadow-lg shadow-[hsl(var(--primary))]/20'
            )}>
              <Terminal className="w-4 h-4 text-[hsl(var(--background))]" />
            </div>
            <span className="font-semibold text-[hsl(var(--foreground))]">Agent Monitor</span>
          </div>

          {/* Page Title (Desktop) */}
          {title && (
            <div className="hidden md:flex items-center gap-3">
              <div className="h-6 w-px bg-[hsl(var(--border))]" />
              <h1 className="text-sm font-medium text-[hsl(var(--foreground))]">
                {title}
              </h1>
            </div>
          )}
        </div>

        {/* Right Section */}
        <div className="flex items-center gap-3 relative z-10">
          {/* System Status */}
          <div className="hidden lg:flex items-center gap-3 mr-2">
            <div className="flex items-center gap-2 text-xs text-[hsl(var(--muted-foreground))]">
              <Activity className="w-3.5 h-3.5 text-[hsl(var(--primary))]" />
              <span className="font-mono">SYS</span>
            </div>
            <div className="h-4 w-px bg-[hsl(var(--border))]" />
          </div>

          {/* Connection Status - Enhanced */}
          <Tooltip>
            <TooltipTrigger asChild>
              <div
                className={cn(
                  'flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium',
                  'border transition-all duration-300',
                  // Connected state
                  connectionState === 'connected' && cn(
                    'bg-[hsl(var(--success))]/5',
                    'text-[hsl(var(--success))]',
                    'border-[hsl(var(--success))]/20',
                    'shadow-sm shadow-[hsl(var(--success))]/10'
                  ),
                  // Connecting/Reconnecting state
                  (connectionState === 'connecting' || connectionState === 'reconnecting') && cn(
                    'bg-[hsl(var(--warning))]/10',
                    'text-[hsl(var(--warning))]',
                    'border-[hsl(var(--warning))]/30',
                    'animate-pulse'
                  ),
                  // Disconnected state
                  connectionState === 'disconnected' && cn(
                    'bg-[hsl(var(--destructive))]/10',
                    'text-[hsl(var(--destructive))]',
                    'border-[hsl(var(--destructive))]/20'
                  )
                )}
                role="status"
                aria-live="polite"
              >
                {/* Connected */}
                {connectionState === 'connected' && (
                  <>
                    <div className="relative">
                      <Wifi className="h-3.5 w-3.5" />
                      <div className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full bg-[hsl(var(--success))]" />
                    </div>
                    <span className="hidden sm:inline font-mono tracking-tight">ONLINE</span>
                  </>
                )}

                {/* Connecting */}
                {connectionState === 'connecting' && (
                  <>
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    <span className="hidden sm:inline font-mono tracking-tight">CONNECTING</span>
                  </>
                )}

                {/* Reconnecting */}
                {connectionState === 'reconnecting' && (
                  <>
                    <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                    <span className="hidden sm:inline font-mono tracking-tight">
                      RETRY {reconnectAttempts}/{maxReconnectAttempts}
                    </span>
                  </>
                )}

                {/* Disconnected */}
                {connectionState === 'disconnected' && (
                  <>
                    <WifiOff className="h-3.5 w-3.5" />
                    <span className="hidden sm:inline font-mono tracking-tight">OFFLINE</span>
                  </>
                )}
              </div>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="max-w-xs">
              <div className="space-y-1">
                <p className="font-medium">
                  {connectionState === 'connected' && 'WebSocket connected'}
                  {connectionState === 'connecting' && 'Establishing connection...'}
                  {connectionState === 'reconnecting' && `Reconnecting (attempt ${reconnectAttempts}/${maxReconnectAttempts})...`}
                  {connectionState === 'disconnected' && 'Connection lost'}
                </p>
                {lastError && connectionState === 'disconnected' && (
                  <p className="text-xs text-[hsl(var(--muted-foreground))]">{lastError}</p>
                )}
              </div>
            </TooltipContent>
          </Tooltip>

          {/* Manual Reconnect Button (shown when disconnected) */}
          {connectionState === 'disconnected' && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => {
                    resetReconnectAttempts()
                    onManualReconnect?.()
                  }}
                  className={cn(
                    'h-8 w-8 rounded-lg',
                    'bg-[hsl(var(--primary))]/10 hover:bg-[hsl(var(--primary))]/20',
                    'text-[hsl(var(--primary))]',
                    'border border-[hsl(var(--primary))]/20'
                  )}
                  aria-label="Reconnect to server"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Reconnect</TooltipContent>
            </Tooltip>
          )}

          {/* Divider */}
          <div className="hidden md:block h-4 w-px bg-[hsl(var(--border))]" />

          {/* Time Display */}
          <time
            className={cn(
              'hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg',
              'bg-[hsl(var(--muted))]/50 border border-[hsl(var(--border))]',
              'text-xs font-mono text-[hsl(var(--foreground))]',
              'tabular-nums tracking-tight'
            )}
            dateTime={currentTime.toISOString()}
          >
            <span className="text-[hsl(var(--primary))]">{formatTime(currentTime).split(':')[0]}</span>
            <span className="text-[hsl(var(--muted-foreground))] animate-pulse">:</span>
            <span>{formatTime(currentTime).split(':')[1]}</span>
            <span className="text-[hsl(var(--muted-foreground))] animate-pulse">:</span>
            <span className="text-[hsl(var(--muted-foreground))]">{formatTime(currentTime).split(':')[2]}</span>
          </time>

          {/* Divider */}
          <div className="hidden md:block h-4 w-px bg-[hsl(var(--border))]" />

          {/* Theme Toggle */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleTheme}
                className={cn(
                  'h-9 w-9 rounded-lg',
                  'hover:bg-[hsl(var(--muted))]',
                  'border border-transparent hover:border-[hsl(var(--border))]',
                  'transition-all duration-200'
                )}
                aria-label={`Switch to ${resolvedTheme === 'dark' ? 'light' : 'dark'} mode`}
              >
                {resolvedTheme === 'dark' ? (
                  <Sun className="h-4 w-4 text-[hsl(var(--warning))]" />
                ) : (
                  <Moon className="h-4 w-4 text-[hsl(var(--primary))]" />
                )}
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              {resolvedTheme === 'dark' ? 'Light mode' : 'Dark mode'}
            </TooltipContent>
          </Tooltip>

          {/* Chat Panel Toggle (Mobile) */}
          {showChatButton && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className={cn(
                    'md:hidden h-9 w-9 rounded-lg',
                    isChatPanelOpen && 'bg-[hsl(var(--primary))]/10 text-[hsl(var(--primary))]'
                  )}
                  onClick={onChatPanelToggle}
                  aria-label={isChatPanelOpen ? 'Close chat' : 'Open chat'}
                  aria-expanded={isChatPanelOpen}
                >
                  <MessageSquare className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                {isChatPanelOpen ? 'Close chat' : 'Open chat'}
              </TooltipContent>
            </Tooltip>
          )}
        </div>
      </header>
    </TooltipProvider>
  )
}

export default Header
