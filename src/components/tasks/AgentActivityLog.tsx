import { useState } from 'react';
import type { AgentLog, AgentLogType } from '../../types';

interface AgentActivityLogProps {
  logs: AgentLog[];
  autoScroll?: boolean;
}

const logTypeConfig: Record<AgentLogType, { icon: string; color: string; label: string }> = {
  info: { icon: '📘', color: 'text-blue-400', label: 'Info' },
  decision: { icon: '🎯', color: 'text-purple-400', label: 'Decision' },
  warning: { icon: '⚠️', color: 'text-yellow-400', label: 'Warning' },
  error: { icon: '❌', color: 'text-red-400', label: 'Error' },
  a2a_call: { icon: '📞', color: 'text-cyan-400', label: 'Agent Call' },
  a2a_response: { icon: '💬', color: 'text-green-400', label: 'Agent Response' },
};

export function AgentActivityLog({ logs, autoScroll = false }: AgentActivityLogProps) {
  const [filter, setFilter] = useState<AgentLogType | 'all'>('all');
  const [expandedLogs, setExpandedLogs] = useState<Set<string>>(new Set());

  const filteredLogs = logs.filter(log => filter === 'all' || log.type === filter);

  const toggleExpand = (logId: string) => {
    setExpandedLogs(prev => {
      const newSet = new Set(prev);
      if (newSet.has(logId)) {
        newSet.delete(logId);
      } else {
        newSet.add(logId);
      }
      return newSet;
    });
  };

  return (
    <div className="flex flex-col h-full">
      {/* Filter Controls */}
      <div className="flex items-center gap-2 mb-4 flex-wrap">
        <button
          onClick={() => setFilter('all')}
          className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
            filter === 'all'
              ? 'bg-slate-600 text-white'
              : 'bg-slate-700/50 text-slate-400 hover:text-white'
          }`}
        >
          All
        </button>
        <button
          onClick={() => setFilter('decision')}
          className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
            filter === 'decision'
              ? 'bg-purple-600 text-white'
              : 'bg-slate-700/50 text-slate-400 hover:text-white'
          }`}
        >
          🎯 Decisions
        </button>
        <button
          onClick={() => setFilter('warning')}
          className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
            filter === 'warning'
              ? 'bg-yellow-600 text-white'
              : 'bg-slate-700/50 text-slate-400 hover:text-white'
          }`}
        >
          ⚠️ Warnings
        </button>
        <button
          onClick={() => setFilter('error')}
          className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
            filter === 'error'
              ? 'bg-red-600 text-white'
              : 'bg-slate-700/50 text-slate-400 hover:text-white'
          }`}
        >
          ❌ Errors
        </button>
      </div>

      {/* Log Timeline */}
      <div className={`flex-1 overflow-y-auto space-y-2 ${autoScroll ? 'scroll-smooth' : ''}`}>
        {filteredLogs.length === 0 ? (
          <div className="text-center py-12 text-slate-500">
            <p className="text-sm">No activity logs yet</p>
            <p className="text-xs mt-1">Agent actions will appear here</p>
          </div>
        ) : (
          <div className="relative">
            {/* Timeline Line */}
            <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-slate-700"></div>

            {/* Log Items */}
            {filteredLogs.map((log, index) => (
              <AgentLogItem
                key={log.id}
                log={log}
                isExpanded={expandedLogs.has(log.id)}
                onToggleExpand={() => toggleExpand(log.id)}
                isLatest={index === filteredLogs.length - 1}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

interface AgentLogItemProps {
  log: AgentLog;
  isExpanded: boolean;
  onToggleExpand: () => void;
  isLatest: boolean;
}

function AgentLogItem({ log, isExpanded, onToggleExpand, isLatest }: AgentLogItemProps) {
  const config = logTypeConfig[log.type];
  const hasDetails = Boolean(log.details);
  const isA2A = log.type === 'a2a_call' || log.type === 'a2a_response';

  return (
    <div className={`relative pl-12 pr-4 pb-3 ${isLatest ? 'pb-0' : ''}`}>
      {/* Timeline Dot */}
      <div
        className={`absolute left-2 w-5 h-5 rounded-full border-2 border-slate-800 flex items-center justify-center text-xs ${
          log.type === 'info' ? 'bg-blue-500' :
          log.type === 'decision' ? 'bg-purple-500' :
          log.type === 'warning' ? 'bg-yellow-500' :
          log.type === 'error' ? 'bg-red-500' :
          log.type === 'a2a_call' ? 'bg-cyan-500' :
          'bg-green-500'
        }`}
      >
        {config.icon}
      </div>

      {/* Log Content */}
      <div className={`rounded-lg p-3 border ${
        isA2A
          ? 'bg-cyan-500/5 border-cyan-500/30'
          : 'bg-slate-700/50 border-slate-600'
      }`}>
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className={`text-xs font-medium ${config.color}`}>
                {log.agentName}
              </span>
              {isA2A && (
                <span className="text-xs text-cyan-400">
                  {log.type === 'a2a_call' ? '→' : '←'}
                </span>
              )}
              <span className="text-xs text-slate-500">
                {formatTimestamp(log.timestamp)}
              </span>
            </div>
            <p className={`text-sm ${isA2A ? 'text-cyan-100' : 'text-white'}`}>
              {log.message}
            </p>
          </div>
          {hasDetails && (
            <button
              onClick={onToggleExpand}
              className="p-1 text-slate-400 hover:text-white transition-colors"
              title={isExpanded ? 'Collapse' : 'Expand'}
            >
              <svg
                className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          )}
        </div>

        {/* Expanded Details */}
        {isExpanded && hasDetails && (
          <div className="mt-3 pt-3 border-t border-slate-600">
            <p className="text-xs text-slate-300 whitespace-pre-wrap">{log.details}</p>
          </div>
        )}
      </div>
    </div>
  );
}

function formatTimestamp(date: Date): string {
  const d = new Date(date);
  const hours = d.getHours().toString().padStart(2, '0');
  const minutes = d.getMinutes().toString().padStart(2, '0');
  const seconds = d.getSeconds().toString().padStart(2, '0');
  return `${hours}:${minutes}:${seconds}`;
}
