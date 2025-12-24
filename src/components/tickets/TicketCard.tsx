import type { Ticket, TicketStatus } from '../../types';

interface TicketCardProps {
  ticket: Ticket;
  onApprove?: () => void;
  onReject?: () => void;
  onSelectOption?: (optionId: string) => void;
}

const statusConfig: Record<TicketStatus, { label: string; color: string; bgColor: string }> = {
  pending_approval: { label: '승인 대기', color: 'text-amber-400', bgColor: 'bg-amber-500/20' },
  approved: { label: '승인됨', color: 'text-green-400', bgColor: 'bg-green-500/20' },
  in_progress: { label: '진행 중', color: 'text-blue-400', bgColor: 'bg-blue-500/20' },
  completed: { label: '완료', color: 'text-slate-400', bgColor: 'bg-slate-500/20' },
  rejected: { label: '거부됨', color: 'text-red-400', bgColor: 'bg-red-500/20' },
};

const priorityConfig = {
  low: { label: '낮음', color: 'text-slate-400' },
  medium: { label: '보통', color: 'text-blue-400' },
  high: { label: '높음', color: 'text-orange-400' },
  urgent: { label: '긴급', color: 'text-red-400' },
};

export function TicketCard({ ticket, onApprove, onReject, onSelectOption }: TicketCardProps) {
  const status = statusConfig[ticket.status];
  const priority = priorityConfig[ticket.priority];
  const isPendingApproval = ticket.status === 'pending_approval';

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-700 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`px-2 py-0.5 rounded text-xs ${status.bgColor} ${status.color}`}>
            {status.label}
          </span>
          <span className={`text-xs ${priority.color}`}>
            {priority.label}
          </span>
        </div>
        <span className="text-xs text-slate-500">
          {formatDate(ticket.createdAt)}
        </span>
      </div>

      {/* Content */}
      <div className="p-4 space-y-3">
        {/* Purpose (Why) */}
        <div>
          <h4 className="text-xs font-medium text-slate-500 uppercase mb-1">목적 (Why)</h4>
          <p className="text-sm text-white">{ticket.purpose}</p>
        </div>

        {/* Content (What) */}
        <div>
          <h4 className="text-xs font-medium text-slate-500 uppercase mb-1">작업 내용 (What)</h4>
          <p className="text-sm text-slate-300">{ticket.content}</p>
        </div>

        {/* Decision Required */}
        {ticket.decisionRequired && (
          <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg">
            <h4 className="text-xs font-medium text-amber-400 uppercase mb-1">결정 필요</h4>
            <p className="text-sm text-amber-200">{ticket.decisionRequired}</p>
          </div>
        )}

        {/* Options */}
        {ticket.options.length > 0 && isPendingApproval && (
          <div>
            <h4 className="text-xs font-medium text-slate-500 uppercase mb-2">선택지</h4>
            <div className="space-y-2">
              {ticket.options.map(option => (
                <button
                  key={option.id}
                  type="button"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log('[TicketCard] Option clicked:', option.id, 'onSelectOption:', !!onSelectOption);
                    onSelectOption?.(option.id);
                  }}
                  className={`
                    w-full text-left p-3 rounded-lg border transition-all cursor-pointer
                    ${option.isRecommended
                      ? 'border-blue-500/50 bg-blue-500/10 hover:bg-blue-500/20 hover:border-blue-500/70'
                      : 'border-slate-600 bg-slate-700/50 hover:bg-slate-700 hover:border-slate-500'
                    }
                    focus:outline-none focus:ring-2 focus:ring-blue-500/50
                  `}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-medium text-white">{option.label}</span>
                    {option.isRecommended && (
                      <span className="px-1.5 py-0.5 bg-blue-500 text-white text-xs rounded">
                        추천
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-400">{option.description}</p>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Execution Plan */}
        <div>
          <h4 className="text-xs font-medium text-slate-500 uppercase mb-1">실행 계획</h4>
          <p className="text-sm text-slate-400">{ticket.executionPlan}</p>
        </div>
      </div>

      {/* Actions */}
      {isPendingApproval && ticket.options.length === 0 && (
        <div className="px-4 py-3 border-t border-slate-700 flex gap-2">
          <button
            onClick={onApprove}
            className="flex-1 py-2 bg-green-600 hover:bg-green-500 text-white rounded-lg text-sm font-medium transition-colors"
          >
            승인
          </button>
          <button
            onClick={onReject}
            className="flex-1 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg text-sm font-medium transition-colors"
          >
            거부
          </button>
        </div>
      )}
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
