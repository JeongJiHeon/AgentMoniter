import type { ApprovalRequest } from '../../types';

interface ApprovalQueueProps {
  requests: ApprovalRequest[];
  onRespond?: (requestId: string, response: 'approve' | 'reject' | string) => void;
}

const requestTypeConfig = {
  proceed: { label: '진행 확인', icon: '?' },
  select_option: { label: '옵션 선택', icon: '!' },
  prioritize: { label: '우선순위 결정', icon: '#' },
};

export function ApprovalQueue({ requests, onRespond }: ApprovalQueueProps) {
  if (requests.length === 0) {
    return (
      <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
        <h2 className="text-lg font-semibold text-white mb-4">승인 대기</h2>
        <div className="text-center py-8 text-slate-500">
          대기 중인 요청이 없습니다
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-white">승인 대기</h2>
        <span className="px-2 py-1 bg-red-500/20 text-red-400 rounded-full text-xs font-medium">
          {requests.length}건 대기
        </span>
      </div>

      <div className="space-y-3">
        {requests.map((request, index) => (
          <ApprovalRequestCard
            key={request.id}
            request={request}
            isFirst={index === 0}
            onRespond={(response) => onRespond?.(request.id, response)}
          />
        ))}
      </div>
    </div>
  );
}

interface ApprovalRequestCardProps {
  request: ApprovalRequest;
  isFirst: boolean;
  onRespond?: (response: 'approve' | 'reject' | string) => void;
}

function ApprovalRequestCard({ request, isFirst, onRespond }: ApprovalRequestCardProps) {
  const typeConfig = requestTypeConfig[request.type];

  return (
    <div
      className={`
        p-4 rounded-lg border transition-all
        ${isFirst
          ? 'bg-amber-500/10 border-amber-500/50 ring-2 ring-amber-500/30'
          : 'bg-slate-800 border-slate-700'
        }
      `}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="w-6 h-6 bg-amber-500/20 text-amber-400 rounded flex items-center justify-center text-sm font-bold">
            {typeConfig.icon}
          </span>
          <span className="text-xs text-amber-400 font-medium">{typeConfig.label}</span>
        </div>
        <span className="text-xs text-slate-500">
          {formatRelativeTime(request.createdAt)}
        </span>
      </div>

      {/* Message */}
      <p className={`text-sm mb-4 ${isFirst ? 'text-white' : 'text-slate-300'}`}>
        {request.message}
      </p>

      {/* Options (for select_option type) */}
      {request.type === 'select_option' && request.options && (
        <div className="space-y-2 mb-4">
          {request.options.map(option => (
            <button
              key={option.id}
              onClick={() => onRespond?.(option.id)}
              className={`
                w-full text-left p-3 rounded-lg border transition-all
                ${option.isRecommended
                  ? 'border-blue-500/50 bg-blue-500/10 hover:bg-blue-500/20'
                  : 'border-slate-600 bg-slate-700/50 hover:bg-slate-700'
                }
              `}
            >
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-white">{option.label}</span>
                {option.isRecommended && (
                  <span className="px-1.5 py-0.5 bg-blue-500 text-white text-xs rounded">
                    추천
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-1">{option.description}</p>
            </button>
          ))}
        </div>
      )}

      {/* Actions (for proceed type) */}
      {request.type === 'proceed' && (
        <div className="flex gap-2">
          <button
            onClick={() => onRespond?.('approve')}
            className="flex-1 py-2 bg-green-600 hover:bg-green-500 text-white rounded-lg text-sm font-medium transition-colors"
          >
            진행
          </button>
          <button
            onClick={() => onRespond?.('reject')}
            className="flex-1 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg text-sm font-medium transition-colors"
          >
            거부
          </button>
        </div>
      )}

      {/* Actions (for prioritize type) */}
      {request.type === 'prioritize' && (
        <div className="flex gap-2">
          <button
            onClick={() => onRespond?.('high')}
            className="flex-1 py-2 bg-orange-600 hover:bg-orange-500 text-white rounded-lg text-sm font-medium transition-colors"
          >
            높음
          </button>
          <button
            onClick={() => onRespond?.('medium')}
            className="flex-1 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors"
          >
            보통
          </button>
          <button
            onClick={() => onRespond?.('low')}
            className="flex-1 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg text-sm font-medium transition-colors"
          >
            낮음
          </button>
        </div>
      )}
    </div>
  );
}

function formatRelativeTime(date: Date): string {
  const now = new Date();
  const diff = now.getTime() - new Date(date).getTime();
  const minutes = Math.floor(diff / 60000);

  if (minutes < 1) return '방금 전';
  if (minutes < 60) return `${minutes}분 전`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}시간 전`;
  return `${Math.floor(hours / 24)}일 전`;
}
