import { useState } from 'react';
import type { CustomAgentConfig, MCPService } from '../../types';

interface AgentSettingsProps {
  agents: CustomAgentConfig[];
  availableMCPs: MCPService[];
  onUpdateAgent: (id: string, updates: Partial<CustomAgentConfig>) => void;
  onDeleteAgent: (id: string) => void;
}

export function AgentSettings({
  agents,
  availableMCPs,
  onUpdateAgent,
  onDeleteAgent,
}: AgentSettingsProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editData, setEditData] = useState<Partial<CustomAgentConfig>>({});
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const handleStartEdit = (agent: CustomAgentConfig) => {
    setEditingId(agent.id);
    setEditData({
      name: agent.name,
      description: agent.description,
      systemPrompt: agent.systemPrompt,
    });
  };

  const handleSaveEdit = (id: string) => {
    if (editData.name?.trim()) {
      onUpdateAgent(id, {
        ...editData,
        updatedAt: new Date(),
      });
    }
    setEditingId(null);
    setEditData({});
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditData({});
  };

  const handleToggleActive = (agent: CustomAgentConfig) => {
    onUpdateAgent(agent.id, { isActive: !agent.isActive });
  };

  const handleDelete = (id: string) => {
    onDeleteAgent(id);
    setConfirmDeleteId(null);
  };

  const getMCPNames = (mcpIds: string[]) => {
    return mcpIds
      .map(id => availableMCPs.find(m => m.id === id)?.name)
      .filter(Boolean)
      .join(', ');
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-lg font-semibold text-white">Agent 관리</h2>
        <p className="text-sm text-slate-400">생성된 Agent를 관리합니다</p>
      </div>

      {/* Agent List */}
      {agents.length === 0 ? (
        <div className="text-center py-12 bg-slate-800/50 rounded-xl border border-slate-700">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-slate-700 flex items-center justify-center">
            <svg className="w-8 h-8 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
          </div>
          <p className="text-slate-400">생성된 Agent가 없습니다</p>
          <p className="text-sm text-slate-500 mt-1">대시보드에서 새 Agent를 생성하세요</p>
        </div>
      ) : (
        <div className="space-y-4">
          {agents.map(agent => (
            <div
              key={agent.id}
              className={`bg-slate-800/50 rounded-xl border transition-all ${
                agent.isActive
                  ? 'border-slate-700'
                  : 'border-slate-700/50 opacity-60'
              }`}
            >
              {editingId === agent.id ? (
                // Edit Mode
                <div className="p-4 space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">
                      이름
                    </label>
                    <input
                      type="text"
                      value={editData.name || ''}
                      onChange={(e) => setEditData(prev => ({ ...prev, name: e.target.value }))}
                      className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">
                      설명
                    </label>
                    <input
                      type="text"
                      value={editData.description || ''}
                      onChange={(e) => setEditData(prev => ({ ...prev, description: e.target.value }))}
                      className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-1">
                      시스템 프롬프트
                    </label>
                    <textarea
                      value={editData.systemPrompt || ''}
                      onChange={(e) => setEditData(prev => ({ ...prev, systemPrompt: e.target.value }))}
                      className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500 resize-none"
                      rows={3}
                    />
                  </div>
                  <div className="flex justify-end gap-2">
                    <button
                      onClick={handleCancelEdit}
                      className="px-3 py-1.5 text-sm text-slate-400 hover:text-white transition-colors"
                    >
                      취소
                    </button>
                    <button
                      onClick={() => handleSaveEdit(agent.id)}
                      className="px-4 py-1.5 text-sm bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors"
                    >
                      저장
                    </button>
                  </div>
                </div>
              ) : (
                // View Mode
                <div className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="font-medium text-white">{agent.name}</h3>
                        <span className={`px-1.5 py-0.5 text-xs rounded ${
                          agent.isActive
                            ? 'bg-green-500/20 text-green-400'
                            : 'bg-slate-500/20 text-slate-400'
                        }`}>
                          {agent.isActive ? '활성' : '비활성'}
                        </span>
                        <span className="px-1.5 py-0.5 bg-slate-500/20 text-slate-400 text-xs rounded">
                          {agent.type}
                        </span>
                      </div>
                      {agent.description && (
                        <p className="text-sm text-slate-400 mt-1">{agent.description}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleToggleActive(agent)}
                        className={`p-1.5 rounded transition-colors ${
                          agent.isActive
                            ? 'text-green-400 hover:bg-green-500/20'
                            : 'text-slate-400 hover:bg-slate-700'
                        }`}
                        title={agent.isActive ? '비활성화' : '활성화'}
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5.636 18.364a9 9 0 010-12.728m12.728 0a9 9 0 010 12.728m-9.9-2.829a5 5 0 010-7.07m7.072 0a5 5 0 010 7.07M13 12a1 1 0 11-2 0 1 1 0 012 0z" />
                        </svg>
                      </button>
                      <button
                        onClick={() => handleStartEdit(agent)}
                        className="p-1.5 text-slate-400 hover:text-white rounded hover:bg-slate-700 transition-colors"
                        title="수정"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                      </button>
                      <button
                        onClick={() => setConfirmDeleteId(agent.id)}
                        className="p-1.5 text-slate-400 hover:text-red-400 rounded hover:bg-red-500/10 transition-colors"
                        title="삭제"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </div>

                  {/* Details */}
                  <div className="mt-4 pt-4 border-t border-slate-700 space-y-2">
                    {agent.systemPrompt && (
                      <div>
                        <p className="text-xs text-slate-500">시스템 프롬프트</p>
                        <p className="text-sm text-slate-400 mt-0.5 line-clamp-2">{agent.systemPrompt}</p>
                      </div>
                    )}
                    {agent.constraints.length > 0 && (
                      <div>
                        <p className="text-xs text-slate-500">제약 조건</p>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {agent.constraints.map((c, i) => (
                            <span key={i} className="px-1.5 py-0.5 bg-red-500/10 border border-red-500/30 rounded text-xs text-red-400">
                              {c}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    {agent.allowedMCPs.length > 0 && (
                      <div>
                        <p className="text-xs text-slate-500">허용된 MCP</p>
                        <p className="text-sm text-slate-400 mt-0.5">{getMCPNames(agent.allowedMCPs)}</p>
                      </div>
                    )}
                    <div className="flex items-center gap-4 text-xs text-slate-500">
                      <span>생성: {new Date(agent.createdAt).toLocaleDateString('ko-KR')}</span>
                      <span>수정: {new Date(agent.updatedAt).toLocaleDateString('ko-KR')}</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Delete Confirmation */}
              {confirmDeleteId === agent.id && (
                <div className="px-4 py-3 bg-red-500/10 border-t border-red-500/30">
                  <p className="text-sm text-red-400">정말 이 Agent를 삭제하시겠습니까?</p>
                  <div className="flex gap-2 mt-2">
                    <button
                      onClick={() => handleDelete(agent.id)}
                      className="px-3 py-1 text-sm bg-red-600 hover:bg-red-500 text-white rounded transition-colors"
                    >
                      삭제
                    </button>
                    <button
                      onClick={() => setConfirmDeleteId(null)}
                      className="px-3 py-1 text-sm text-slate-400 hover:text-white transition-colors"
                    >
                      취소
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
