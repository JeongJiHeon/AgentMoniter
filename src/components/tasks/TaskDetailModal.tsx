import { useEffect, useState } from 'react';
import type { Task } from '../../types/task';
import type { Agent, Ticket, ApprovalRequest } from '../../types';

interface TaskDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  task: Task;
  agent?: Agent;
  tickets: Ticket[];
  approvalRequests: ApprovalRequest[];
}

export function TaskDetailModal({
  isOpen,
  onClose,
  task,
  agent,
  tickets,
  approvalRequests,
}: TaskDetailModalProps) {
  const [activeTab, setActiveTab] = useState<'overview' | 'tickets' | 'approvals'>('overview');

  useEffect(() => {
    // ESC 키로 모달 닫기
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
      // 모달 열릴 때 body 스크롤 방지
      document.body.style.overflow = 'hidden';
    }

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const priorityColors = {
    low: 'text-slate-400',
    medium: 'text-blue-400',
    high: 'text-orange-400',
    urgent: 'text-red-400',
  };

  const statusColors = {
    pending: 'text-slate-400',
    in_progress: 'text-blue-400',
    completed: 'text-green-400',
    cancelled: 'text-red-400',
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-slate-800 rounded-xl border border-slate-700 max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-slate-700">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h2 className="text-2xl font-semibold text-white mb-2">{task.title}</h2>
              <div className="flex items-center gap-3 flex-wrap">
                <span className={`text-sm font-medium ${statusColors[task.status]}`}>
                  {task.status === 'pending' && '⏳ 대기 중'}
                  {task.status === 'in_progress' && '🔄 진행 중'}
                  {task.status === 'completed' && '✅ 완료'}
                  {task.status === 'cancelled' && '❌ 취소됨'}
                </span>
                <span className={`text-sm font-medium ${priorityColors[task.priority]}`}>
                  {task.priority === 'urgent' && '🔥 긴급'}
                  {task.priority === 'high' && '⚠️ 높음'}
                  {task.priority === 'medium' && '📌 보통'}
                  {task.priority === 'low' && '📋 낮음'}
                </span>
                {agent && (
                  <span className="text-sm text-blue-400">
                    🤖 {agent.name}
                  </span>
                )}
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 text-slate-400 hover:text-white transition-colors rounded-lg hover:bg-slate-700"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 px-6 pt-4 border-b border-slate-700">
          <button
            onClick={() => setActiveTab('overview')}
            className={`px-4 py-2 text-sm font-medium transition-colors rounded-t-lg ${
              activeTab === 'overview'
                ? 'bg-slate-700 text-white'
                : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
            }`}
          >
            개요
          </button>
          <button
            onClick={() => setActiveTab('tickets')}
            className={`px-4 py-2 text-sm font-medium transition-colors rounded-t-lg ${
              activeTab === 'tickets'
                ? 'bg-slate-700 text-white'
                : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
            }`}
          >
            티켓 ({tickets.length})
          </button>
          <button
            onClick={() => setActiveTab('approvals')}
            className={`px-4 py-2 text-sm font-medium transition-colors rounded-t-lg ${
              activeTab === 'approvals'
                ? 'bg-slate-700 text-white'
                : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
            }`}
          >
            승인 요청 ({approvalRequests.length})
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === 'overview' && (
            <div className="space-y-6">
              {/* 설명 */}
              <div>
                <h3 className="text-sm font-medium text-slate-400 mb-2">설명</h3>
                <p className="text-white whitespace-pre-wrap">{task.description || '설명 없음'}</p>
              </div>

              {/* 태그 */}
              {task.tags.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-slate-400 mb-2">태그</h3>
                  <div className="flex flex-wrap gap-2">
                    {task.tags.map((tag, idx) => (
                      <span key={idx} className="px-3 py-1 bg-slate-700 text-slate-300 text-sm rounded-full">
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* 메타데이터 */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h3 className="text-sm font-medium text-slate-400 mb-1">출처</h3>
                  <p className="text-white">
                    {task.source === 'manual' && '수동 생성'}
                    {task.source === 'slack' && '💬 Slack'}
                    {task.source === 'confluence' && '📄 Confluence'}
                    {task.source === 'email' && '📧 Email'}
                    {task.source === 'other' && '기타'}
                  </p>
                </div>
                {task.sourceReference && (
                  <div>
                    <h3 className="text-sm font-medium text-slate-400 mb-1">원본 참조</h3>
                    <p className="text-slate-300 text-sm truncate">{task.sourceReference}</p>
                  </div>
                )}
                <div>
                  <h3 className="text-sm font-medium text-slate-400 mb-1">생성일</h3>
                  <p className="text-white">
                    {new Date(task.createdAt).toLocaleString('ko-KR')}
                  </p>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-slate-400 mb-1">최종 수정</h3>
                  <p className="text-white">
                    {new Date(task.updatedAt).toLocaleString('ko-KR')}
                  </p>
                </div>
                {task.dueDate && (
                  <div>
                    <h3 className="text-sm font-medium text-slate-400 mb-1">마감일</h3>
                    <p className="text-white">
                      {new Date(task.dueDate).toLocaleString('ko-KR')}
                    </p>
                  </div>
                )}
                {task.completedAt && (
                  <div>
                    <h3 className="text-sm font-medium text-slate-400 mb-1">완료일</h3>
                    <p className="text-green-400">
                      {new Date(task.completedAt).toLocaleString('ko-KR')}
                    </p>
                  </div>
                )}
              </div>

              {/* Agent 진행 상황 */}
              {agent && (
                <div className="p-4 bg-slate-700/50 rounded-lg border border-slate-600">
                  <h3 className="text-sm font-medium text-white mb-3">Agent 진행 상황</h3>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-slate-400">현재 모드</span>
                      <span className="text-sm text-white font-medium">
                        {agent.thinkingMode === 'idle' && '⚪ 대기'}
                        {agent.thinkingMode === 'exploring' && '🔍 탐색 중'}
                        {agent.thinkingMode === 'structuring' && '🏗️ 구조화 중'}
                        {agent.thinkingMode === 'validating' && '✅ 검증 중'}
                        {agent.thinkingMode === 'summarizing' && '📝 요약 중'}
                      </span>
                    </div>
                    {agent.currentTask && (
                      <div>
                        <span className="text-sm text-slate-400">현재 작업</span>
                        <p className="text-sm text-white mt-1">{agent.currentTask}</p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'tickets' && (
            <div className="space-y-3">
              {tickets.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-slate-400">생성된 티켓이 없습니다</p>
                  <p className="text-sm text-slate-500 mt-2">
                    Agent가 작업을 처리하면 티켓이 여기에 표시됩니다
                  </p>
                </div>
              ) : (
                tickets.map(ticket => (
                  <div key={ticket.id} className="p-4 bg-slate-700 rounded-lg border border-slate-600">
                    <div className="flex items-start justify-between mb-2">
                      <h4 className="text-white font-medium">{ticket.purpose}</h4>
                      <span className={`text-xs px-2 py-1 rounded ${
                        ticket.status === 'completed' ? 'bg-green-500/20 text-green-400' :
                        ticket.status === 'approved' ? 'bg-blue-500/20 text-blue-400' :
                        ticket.status === 'rejected' ? 'bg-red-500/20 text-red-400' :
                        'bg-slate-600 text-slate-300'
                      }`}>
                        {ticket.status === 'pending_approval' && '승인 대기'}
                        {ticket.status === 'approved' && '승인됨'}
                        {ticket.status === 'in_progress' && '진행 중'}
                        {ticket.status === 'completed' && '완료'}
                        {ticket.status === 'rejected' && '거부됨'}
                      </span>
                    </div>
                    <p className="text-sm text-slate-300 mb-3">{ticket.content}</p>
                    {ticket.executionPlan && (
                      <div className="mt-2 p-2 bg-slate-800 rounded text-xs text-slate-400">
                        <strong className="text-slate-300">실행 계획:</strong> {ticket.executionPlan}
                      </div>
                    )}
                    <div className="mt-2 text-xs text-slate-500">
                      {new Date(ticket.createdAt).toLocaleString('ko-KR')}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {activeTab === 'approvals' && (
            <div className="space-y-3">
              {approvalRequests.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-slate-400">승인 요청이 없습니다</p>
                  <p className="text-sm text-slate-500 mt-2">
                    Agent가 승인이 필요한 작업을 수행하면 여기에 표시됩니다
                  </p>
                </div>
              ) : (
                approvalRequests.map(request => (
                  <div key={request.id} className="p-4 bg-slate-700 rounded-lg border border-slate-600">
                    <div className="flex items-start justify-between mb-2">
                      <h4 className="text-white font-medium">{request.message}</h4>
                      <span className={`text-xs px-2 py-1 rounded ${
                        request.type === 'proceed' ? 'bg-blue-500/20 text-blue-400' :
                        request.type === 'select_option' ? 'bg-purple-500/20 text-purple-400' :
                        'bg-orange-500/20 text-orange-400'
                      }`}>
                        {request.type === 'proceed' && '진행 승인'}
                        {request.type === 'select_option' && '옵션 선택'}
                        {request.type === 'prioritize' && '우선순위'}
                      </span>
                    </div>
                    {request.options && request.options.length > 0 && (
                      <div className="mt-3 space-y-2">
                        <p className="text-xs text-slate-400">옵션:</p>
                        {request.options.map(option => (
                          <div
                            key={option.id}
                            className={`p-2 rounded ${
                              option.isRecommended
                                ? 'bg-blue-500/20 border border-blue-500/30'
                                : 'bg-slate-800 border border-slate-600'
                            }`}
                          >
                            <div className="flex items-center gap-2">
                              <span className="text-sm text-white">{option.label}</span>
                              {option.isRecommended && (
                                <span className="text-xs px-1.5 py-0.5 bg-blue-500 text-white rounded">
                                  추천
                                </span>
                              )}
                            </div>
                            <p className="text-xs text-slate-400 mt-1">{option.description}</p>
                          </div>
                        ))}
                      </div>
                    )}
                    <div className="mt-2 text-xs text-slate-500">
                      {new Date(request.createdAt).toLocaleString('ko-KR')}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-700 flex justify-end">
          <button
            onClick={onClose}
            className="px-6 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
          >
            닫기
          </button>
        </div>
      </div>
    </div>
  );
}
