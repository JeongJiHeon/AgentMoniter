import { Search, Plus, Activity, CheckCircle2, XCircle, Clock, AlertCircle } from 'lucide-react';

interface CommandBarProps {
  stats: {
    total: number;
    pending: number;
    inProgress: number;
    completed: number;
    failed: number;
  };
  searchQuery: string;
  onSearchChange: (query: string) => void;
  onCreateTask: () => void;
  autoAssignMode: 'global' | 'manual';
  onAutoAssignModeChange: (mode: 'global' | 'manual') => void;
}

export function CommandBar({
  stats,
  searchQuery,
  onSearchChange,
  onCreateTask,
  autoAssignMode,
  onAutoAssignModeChange,
}: CommandBarProps) {
  return (
    <div className="relative border-b border-cyan-400/10 bg-gradient-to-r from-[#0d1117]/95 to-[#0a0e1a]/95 backdrop-blur-xl">
      {/* Neon glow line */}
      <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-cyan-400/50 to-transparent" />

      <div className="px-6 py-4">
        <div className="flex items-center justify-between gap-6">
          {/* Left: Title & Stats */}
          <div className="flex items-center gap-6">
            <div>
              <h1 className="text-xl font-bold bg-gradient-to-r from-cyan-400 to-cyan-300 bg-clip-text text-transparent tracking-tight">
                ENHANCED PLANNER
              </h1>
              <p className="text-xs text-gray-500 mt-0.5 tracking-wider">AGENT MONITOR v2.0</p>
            </div>

            {/* Live Stats */}
            <div className="flex items-center gap-3 pl-6 border-l border-cyan-400/10">
              <StatBadge
                icon={Activity}
                label="Total"
                value={stats.total}
                color="cyan"
              />
              <StatBadge
                icon={Clock}
                label="Pending"
                value={stats.pending}
                color="amber"
                pulse={stats.pending > 0}
              />
              <StatBadge
                icon={Activity}
                label="Active"
                value={stats.inProgress}
                color="green"
                pulse={stats.inProgress > 0}
              />
              <StatBadge
                icon={CheckCircle2}
                label="Done"
                value={stats.completed}
                color="emerald"
              />
              {stats.failed > 0 && (
                <StatBadge
                  icon={AlertCircle}
                  label="Failed"
                  value={stats.failed}
                  color="red"
                  pulse
                />
              )}
            </div>
          </div>

          {/* Right: Controls */}
          <div className="flex items-center gap-3">
            {/* Search */}
            <div className="relative group">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-cyan-400/50 group-focus-within:text-cyan-400 transition-colors" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => onSearchChange(e.target.value)}
                placeholder="Search tasks..."
                className="w-64 bg-[#1a1f2e]/50 border border-cyan-400/20 rounded-lg pl-10 pr-4 py-2 text-sm text-gray-300 placeholder-gray-600 focus:outline-none focus:border-cyan-400/50 focus:ring-1 focus:ring-cyan-400/30 transition-all"
              />
              {searchQuery && (
                <button
                  onClick={() => onSearchChange('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-400"
                >
                  <XCircle className="w-4 h-4" />
                </button>
              )}
            </div>

            {/* Auto-assign toggle */}
            <button
              onClick={() => onAutoAssignModeChange(autoAssignMode === 'global' ? 'manual' : 'global')}
              className={`px-3 py-2 rounded-lg text-xs font-medium transition-all border ${
                autoAssignMode === 'global'
                  ? 'bg-cyan-500/20 border-cyan-400/50 text-cyan-300'
                  : 'bg-gray-800/50 border-gray-700/50 text-gray-400 hover:border-gray-600'
              }`}
            >
              <div className="flex items-center gap-2">
                <div className={`w-1.5 h-1.5 rounded-full ${autoAssignMode === 'global' ? 'bg-cyan-400 animate-pulse' : 'bg-gray-600'}`} />
                AUTO-ASSIGN
              </div>
            </button>

            {/* Create Task Button */}
            <button
              onClick={onCreateTask}
              className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-cyan-500 to-cyan-600 hover:from-cyan-400 hover:to-cyan-500 text-white rounded-lg text-sm font-medium transition-all shadow-lg shadow-cyan-500/20 hover:shadow-cyan-500/40 border border-cyan-400/50"
            >
              <Plus className="w-4 h-4" />
              New Task
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

interface StatBadgeProps {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: number;
  color: 'cyan' | 'amber' | 'green' | 'emerald' | 'red';
  pulse?: boolean;
}

function StatBadge({ icon: Icon, label, value, color, pulse }: StatBadgeProps) {
  const colorClasses = {
    cyan: 'text-cyan-400 bg-cyan-400/10 border-cyan-400/30',
    amber: 'text-amber-400 bg-amber-400/10 border-amber-400/30',
    green: 'text-green-400 bg-green-400/10 border-green-400/30',
    emerald: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/30',
    red: 'text-red-400 bg-red-400/10 border-red-400/30',
  };

  return (
    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-md border ${colorClasses[color]} backdrop-blur-sm`}>
      <Icon className={`w-3.5 h-3.5 ${pulse ? 'animate-pulse' : ''}`} />
      <div className="flex items-baseline gap-1.5">
        <span className="text-xs opacity-70 uppercase tracking-wide">{label}</span>
        <span className="text-sm font-bold tabular-nums">{value}</span>
      </div>
    </div>
  );
}
