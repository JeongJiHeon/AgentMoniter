import type { ReactNode } from 'react';

type TabType = 'dashboard' | 'tasks' | 'personalization' | 'settings';

interface DashboardLayoutProps {
  children: ReactNode;
  activeTab: TabType;
  onTabChange: (tab: TabType) => void;
  rightPanel?: ReactNode;
}

export function DashboardLayout({ children, activeTab, onTabChange, rightPanel }: DashboardLayoutProps) {
  return (
    <div className="h-screen bg-slate-900 flex overflow-hidden">
      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Header */}
        <header className="bg-slate-800 border-b border-slate-700 flex-shrink-0">
          <div className="px-6 py-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">AM</span>
              </div>
              <h1 className="text-xl font-semibold text-white">Agent Monitor</h1>
            </div>
            <div className="flex items-center gap-4">
              <ConnectionStatus />
              <span className="text-slate-400 text-sm">
                {new Date().toLocaleString('ko-KR')}
              </span>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="px-6 flex gap-1">
            <TabButton
              isActive={activeTab === 'tasks'}
              onClick={() => onTabChange('tasks')}
              icon={
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                </svg>
              }
            >
              Tasks
            </TabButton>
            <TabButton
              isActive={activeTab === 'dashboard'}
              onClick={() => onTabChange('dashboard')}
              icon={
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
                </svg>
              }
            >
              대시보드
            </TabButton>
            <TabButton
              isActive={activeTab === 'personalization'}
              onClick={() => onTabChange('personalization')}
              icon={
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              }
            >
              개인화 정보
            </TabButton>
            <TabButton
              isActive={activeTab === 'settings'}
              onClick={() => onTabChange('settings')}
              icon={
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              }
            >
              설정
            </TabButton>
          </nav>
        </header>

        {/* Main Content */}
        <main className="p-6 flex-1 overflow-auto">
          {children}
        </main>
      </div>

      {/* Right Panel - Chat */}
      {rightPanel && (
        <div className="w-96 border-l border-slate-700 bg-slate-800 flex flex-col flex-shrink-0 h-full overflow-hidden">
          {rightPanel}
        </div>
      )}
    </div>
  );
}

interface TabButtonProps {
  children: ReactNode;
  isActive: boolean;
  onClick: () => void;
  icon?: ReactNode;
}

function TabButton({ children, isActive, onClick, icon }: TabButtonProps) {
  return (
    <button
      onClick={onClick}
      className={`
        flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-t-lg transition-colors
        ${isActive
          ? 'bg-slate-900 text-white border-t border-l border-r border-slate-700'
          : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
        }
      `}
    >
      {icon}
      {children}
    </button>
  );
}

function ConnectionStatus() {
  // TODO: WebSocket 연결 상태를 props로 받아서 표시
  const isConnected = false; // 초기 상태는 미연결

  return (
    <div className="flex items-center gap-2">
      <div
        className={`w-2 h-2 rounded-full ${
          isConnected ? 'bg-green-500 animate-pulse' : 'bg-slate-500'
        }`}
      />
      <span className={`text-sm ${isConnected ? 'text-green-400' : 'text-slate-400'}`}>
        {isConnected ? '연결됨' : '연결 대기'}
      </span>
    </div>
  );
}
