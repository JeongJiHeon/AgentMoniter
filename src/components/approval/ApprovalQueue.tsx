import { useState, useMemo } from 'react';
import type { ApprovalRequest } from '../../types';

type ApprovalRequestType = 'proceed' | 'select_option' | 'prioritize';
type SortOption = 'newest' | 'oldest';

interface ApprovalQueueProps {
  requests: ApprovalRequest[];
  onRespond?: (requestId: string, response: 'approve' | 'reject' | string) => void;
}

const requestTypeConfig: Record<ApprovalRequestType, { label: string; icon: string }> = {
  proceed: { label: '진행 확인', icon: '?' },
  select_option: { label: '옵션 선택', icon: '!' },
  prioritize: { label: '우선순위 결정', icon: '#' },
};

export function ApprovalQueue({ requests, onRespond }: ApprovalQueueProps) {
  const [filterType, setFilterType] = useState<ApprovalRequestType | 'all'>('all');
  const [sortOption, setSortOption] = useState<SortOption>('newest');
  const [searchQuery, setSearchQuery] = useState('');

  // Filter and sort requests
  const filteredRequests = useMemo(() => {
    let result = [...requests];

    // Filter by type
    if (filterType !== 'all') {
      result = result.filter(req => req.type === filterType);
    }

    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = result.filter(req =>
        req.message.toLowerCase().includes(query) ||
        req.agentId.toLowerCase().includes(query)
      );
    }

    // Sort
    result.sort((a, b) => {
      const dateA = new Date(a.createdAt).getTime();
      const dateB = new Date(b.createdAt).getTime();
      return sortOption === 'newest' ? dateB - dateA : dateA - dateB;
    });

    return result;
  }, [requests, filterType, sortOption, searchQuery]);

  // Count by type
  const typeCounts = useMemo(() => ({
    all: requests.length,
    proceed: requests.filter(r => r.type === 'proceed').length,
    select_option: requests.filter(r => r.type === 'select_option').length,
    prioritize: requests.filter(r => r.type === 'prioritize').length,
  }), [requests]);

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
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-white">승인 대기</h2>
        <span className="px-2 py-1 bg-red-500/20 text-red-400 rounded-full text-xs font-medium">
          {requests.length}건 대기
        </span>
      </div>

      {/* Search and Filters */}
      <div className="space-y-3 mb-4">
        {/* Search Input */}
        <div className="relative">
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="요청 검색..."
            className="w-full pl-10 pr-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white text-sm placeholder:text-slate-400 focus:outline-none focus:border-blue-500"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        {/* Filter Buttons & Sort */}
        <div className="flex items-center justify-between">
          {/* Type Filter Buttons */}
          <div className="flex gap-1 flex-wrap">
            {(['all', 'proceed', 'select_option', 'prioritize'] as const).map((type) => (
              <button
                key={type}
                onClick={() => setFilterType(type)}
                className={`px-2 py-1 text-xs rounded-lg transition-colors flex items-center gap-1 ${
                  filterType === type
                    ? 'bg-blue-600 text-white'
                    : 'bg-slate-700 text-slate-400 hover:text-white'
                }`}
              >
                {type === 'all' ? '전체' : requestTypeConfig[type].label}
                <span className={`px-1.5 rounded ${
                  filterType === type ? 'bg-blue-500' : 'bg-slate-600'
                }`}>
                  {typeCounts[type]}
                </span>
              </button>
            ))}
          </div>

          {/* Sort Dropdown */}
          <select
            value={sortOption}
            onChange={(e) => setSortOption(e.target.value as SortOption)}
            className="px-2 py-1 bg-slate-700 border border-slate-600 rounded-lg text-white text-xs focus:outline-none focus:border-blue-500"
          >
            <option value="newest">최신순</option>
            <option value="oldest">오래된순</option>
          </select>
        </div>
      </div>

      {/* Results Info */}
      {(filterType !== 'all' || searchQuery) && (
        <div className="mb-3 text-xs text-slate-400">
          {filteredRequests.length}건의 결과
          {filterType !== 'all' && ` (${requestTypeConfig[filterType].label})`}
          {searchQuery && ` - "${searchQuery}"`}
        </div>
      )}

      {/* Request List */}
      <div className="space-y-3">
        {filteredRequests.length === 0 ? (
          <div className="text-center py-8 text-slate-500 text-sm">
            필터 조건에 맞는 요청이 없습니다
          </div>
        ) : (
          filteredRequests.map((request, index) => (
            <ApprovalRequestCard
              key={request.id}
              request={request}
              isFirst={index === 0}
              onRespond={(response) => onRespond?.(request.id, response)}
            />
          ))
        )}
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

      {/* Decision-focused structure */}
      <div className="space-y-3 mb-4">
        {/* What */}
        <div>
          <h4 className="text-xs font-semibold text-slate-400 mb-1">✔ Action</h4>
          <p className={`text-sm ${isFirst ? 'text-white' : 'text-slate-300'}`}>
            {request.message}
          </p>
        </div>

        {/* Why - from type */}
        <div>
          <h4 className="text-xs font-semibold text-slate-400 mb-1">⚠ Reason</h4>
          <p className="text-sm text-slate-300">
            {request.type === 'proceed' && 'Manual approval required for this action'}
            {request.type === 'select_option' && 'Multiple options available - your choice needed'}
            {request.type === 'prioritize' && 'Priority decision required'}
          </p>
        </div>

        {/* Impact - generic for now, can be enhanced with ticket details */}
        <div>
          <h4 className="text-xs font-semibold text-slate-400 mb-1">📄 Impact</h4>
          <p className="text-sm text-slate-300">
            {request.type === 'proceed' && 'Action will be executed immediately after approval'}
            {request.type === 'select_option' && `${request.options?.length || 0} option(s) available`}
            {request.type === 'prioritize' && 'Will affect task execution order'}
          </p>
        </div>
      </div>

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
