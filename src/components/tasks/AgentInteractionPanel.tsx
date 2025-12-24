import { useState } from 'react';
import type { Interaction, InteractionType } from '../../types';

interface AgentInteractionPanelProps {
  interactions: Interaction[];
  onRespond?: (interactionId: string, response: string) => void;
}

const interactionTypeConfig: Record<InteractionType, { icon: string; color: string; label: string }> = {
  clarify: { icon: '❓', color: 'text-blue-400', label: 'Clarify' },
  adjust: { icon: '🔧', color: 'text-purple-400', label: 'Adjust' },
  guide: { icon: '🎯', color: 'text-green-400', label: 'Guide' },
};

export function AgentInteractionPanel({ interactions, onRespond }: AgentInteractionPanelProps) {
  // pending이 먼저, 그 다음 최신순
  const sortedInteractions = [...interactions].sort((a, b) => {
    if (a.status === 'pending' && b.status !== 'pending') return -1;
    if (a.status !== 'pending' && b.status === 'pending') return 1;
    return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
  });

  const pendingCount = interactions.filter(i => i.status === 'pending').length;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="mb-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-white">Agent Interaction</h3>
          {pendingCount > 0 && (
            <span className="px-2 py-1 bg-blue-500/20 text-blue-400 rounded-full text-xs font-medium">
              {pendingCount} pending
            </span>
          )}
        </div>
        <p className="text-sm text-slate-400 mt-1">
          Coordinate and adjust agent behavior
        </p>
      </div>

      {/* Interaction List */}
      <div className="flex-1 overflow-y-auto space-y-3">
        {sortedInteractions.length === 0 ? (
          <div className="text-center py-12 text-slate-500">
            <p className="text-sm">No interactions yet</p>
            <p className="text-xs mt-1">Agent will ask for guidance when needed</p>
          </div>
        ) : (
          sortedInteractions.map((interaction) => (
            <InteractionCard
              key={interaction.id}
              interaction={interaction}
              onRespond={onRespond}
            />
          ))
        )}
      </div>
    </div>
  );
}

interface InteractionCardProps {
  interaction: Interaction;
  onRespond?: (interactionId: string, response: string) => void;
}

function InteractionCard({ interaction, onRespond }: InteractionCardProps) {
  const [customResponse, setCustomResponse] = useState('');
  const config = interactionTypeConfig[interaction.type];
  const isPending = interaction.status === 'pending';

  const handleOptionClick = (optionId: string) => {
    if (onRespond && isPending) {
      onRespond(interaction.id, optionId);
    }
  };

  const handleCustomSubmit = () => {
    if (onRespond && isPending && customResponse.trim()) {
      onRespond(interaction.id, customResponse.trim());
      setCustomResponse('');
    }
  };

  return (
    <div
      className={`p-4 rounded-lg border transition-all ${
        isPending
          ? 'bg-blue-500/10 border-blue-500/50 ring-2 ring-blue-500/30'
          : 'bg-slate-700/50 border-slate-600'
      }`}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className={`text-lg ${config.color}`}>{config.icon}</span>
          <div>
            <span className={`text-xs font-medium ${config.color}`}>{config.label}</span>
            <p className="text-xs text-slate-400">{interaction.agentName}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-xs px-2 py-1 rounded ${
            isPending ? 'bg-blue-500/20 text-blue-400' :
            interaction.status === 'responded' ? 'bg-green-500/20 text-green-400' :
            'bg-slate-600 text-slate-300'
          }`}>
            {interaction.status}
          </span>
          <span className="text-xs text-slate-500">
            {formatRelativeTime(interaction.createdAt)}
          </span>
        </div>
      </div>

      {/* Question */}
      <div className="mb-3">
        <p className={`text-sm ${isPending ? 'text-white font-medium' : 'text-slate-300'}`}>
          {interaction.question}
        </p>
      </div>

      {/* Response Area */}
      {isPending && (
        <div className="space-y-3">
          {/* Options (for clarify type) */}
          {interaction.type === 'clarify' && interaction.options && interaction.options.length > 0 && (
            <div className="space-y-2">
              {interaction.options.map(option => (
                <button
                  key={option.id}
                  onClick={() => handleOptionClick(option.id)}
                  className="w-full text-left p-3 rounded-lg border border-blue-500/30 bg-blue-500/5 hover:bg-blue-500/10 transition-all"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-white">{option.label}</span>
                  </div>
                  {option.description && (
                    <p className="text-xs text-slate-400 mt-1">{option.description}</p>
                  )}
                </button>
              ))}
            </div>
          )}

          {/* Custom Response (for adjust and guide) */}
          {(interaction.type === 'adjust' || interaction.type === 'guide') && (
            <div className="space-y-2">
              <textarea
                value={customResponse}
                onChange={(e) => setCustomResponse(e.target.value)}
                placeholder={
                  interaction.type === 'adjust'
                    ? 'Provide your adjustment...'
                    : 'Provide guidance...'
                }
                className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500 resize-none"
                rows={3}
              />
              <div className="flex gap-2">
                <button
                  onClick={handleCustomSubmit}
                  disabled={!customResponse.trim()}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Submit
                </button>
                <button
                  onClick={() => setCustomResponse('')}
                  className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg text-sm font-medium transition-colors"
                >
                  Clear
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Responded */}
      {!isPending && interaction.userResponse && (
        <div className="mt-3 p-3 bg-slate-800 rounded-lg border border-slate-600">
          <p className="text-xs text-slate-400 mb-1">Your response:</p>
          <p className="text-sm text-white">{interaction.userResponse}</p>
          {interaction.respondedAt && (
            <p className="text-xs text-slate-500 mt-2">
              {new Date(interaction.respondedAt).toLocaleString('ko-KR')}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function formatRelativeTime(date: Date): string {
  const now = new Date();
  const diff = now.getTime() - new Date(date).getTime();
  const minutes = Math.floor(diff / 60000);

  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}
