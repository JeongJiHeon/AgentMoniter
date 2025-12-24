import { useState } from 'react';
import type { MCPService, MCPConnectionStatus } from '../../types';

interface MCPServiceCardProps {
  service: MCPService;
  onToggle: (id: string, enabled: boolean) => void;
  onConnect: (id: string) => void;
  onDisconnect: (id: string) => void;
  onConfigure: (id: string) => void;
  onRemove: (id: string) => void;
}

const statusConfig: Record<MCPConnectionStatus, { label: string; color: string; bgColor: string }> = {
  connected: { label: '연결됨', color: 'text-green-400', bgColor: 'bg-green-500/20' },
  disconnected: { label: '연결 안됨', color: 'text-slate-400', bgColor: 'bg-slate-500/20' },
  connecting: { label: '연결 중...', color: 'text-blue-400', bgColor: 'bg-blue-500/20' },
  error: { label: '오류', color: 'text-red-400', bgColor: 'bg-red-500/20' },
};

const serviceIcons: Record<string, string> = {
  notion: 'N',
  slack: 'S',
  confluence: 'C',
  gmail: 'G',
  'google-docs': 'D',
  'google-calendar': 'C',
  jira: 'J',
  github: 'H',
  custom: '*',
};

export function MCPServiceCard({
  service,
  onToggle,
  onConnect,
  onDisconnect,
  onConfigure,
  onRemove,
}: MCPServiceCardProps) {
  const [showActions, setShowActions] = useState(false);
  const status = statusConfig[service.status];

  return (
    <div
      className={`
        bg-slate-800 rounded-lg border transition-all
        ${service.enabled ? 'border-slate-600' : 'border-slate-700 opacity-60'}
      `}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      <div className="p-4">
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className={`
              w-10 h-10 rounded-lg flex items-center justify-center text-lg font-bold
              ${service.enabled ? 'bg-blue-500/20 text-blue-400' : 'bg-slate-700 text-slate-500'}
            `}>
              {serviceIcons[service.type] || '?'}
            </div>
            <div>
              <h3 className="font-medium text-white">{service.name}</h3>
              <p className="text-xs text-slate-500">{service.type}</p>
            </div>
          </div>

          {/* Toggle Switch */}
          <button
            onClick={() => onToggle(service.id, !service.enabled)}
            className={`
              relative w-11 h-6 rounded-full transition-colors
              ${service.enabled ? 'bg-blue-600' : 'bg-slate-600'}
            `}
          >
            <div
              className={`
                absolute top-1 w-4 h-4 bg-white rounded-full transition-transform
                ${service.enabled ? 'translate-x-6' : 'translate-x-1'}
              `}
            />
          </button>
        </div>

        {/* Description */}
        <p className="text-sm text-slate-400 mb-3">{service.description}</p>

        {/* Status */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className={`px-2 py-0.5 rounded text-xs ${status.bgColor} ${status.color}`}>
              {status.label}
            </span>
            {service.lastConnected && service.status === 'connected' && (
              <span className="text-xs text-slate-500">
                {formatDate(service.lastConnected)}
              </span>
            )}
          </div>

          {/* Action Buttons */}
          <div className={`flex gap-1 transition-opacity ${showActions ? 'opacity-100' : 'opacity-0'}`}>
            {service.status === 'connected' ? (
              <button
                onClick={() => onDisconnect(service.id)}
                className="px-2 py-1 text-xs bg-slate-700 hover:bg-slate-600 text-slate-300 rounded"
              >
                연결 해제
              </button>
            ) : (
              <button
                onClick={() => onConnect(service.id)}
                disabled={!service.enabled}
                className="px-2 py-1 text-xs bg-blue-600 hover:bg-blue-500 text-white rounded disabled:opacity-50"
              >
                연결
              </button>
            )}
            <button
              onClick={() => onConfigure(service.id)}
              className="px-2 py-1 text-xs bg-slate-700 hover:bg-slate-600 text-slate-300 rounded"
            >
              설정
            </button>
            <button
              onClick={() => onRemove(service.id)}
              className="px-2 py-1 text-xs bg-red-600/20 hover:bg-red-600/40 text-red-400 rounded"
            >
              삭제
            </button>
          </div>
        </div>

        {/* Error Message */}
        {service.errorMessage && (
          <div className="mt-2 p-2 bg-red-500/10 border border-red-500/30 rounded text-xs text-red-400">
            {service.errorMessage}
          </div>
        )}
      </div>
    </div>
  );
}

function formatDate(date: Date): string {
  return new Date(date).toLocaleString('ko-KR', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}
