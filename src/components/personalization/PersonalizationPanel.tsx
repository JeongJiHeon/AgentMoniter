import { useState } from 'react';
import type { PersonalizationItem } from '../../types';

interface PersonalizationPanelProps {
  items: PersonalizationItem[];
  onAddItem: (item: Omit<PersonalizationItem, 'id' | 'createdAt' | 'updatedAt'>) => void;
  onUpdateItem: (id: string, content: string) => void;
  onDeleteItem: (id: string) => void;
}

const categoryConfig: Record<PersonalizationItem['category'], { label: string; color: string }> = {
  preference: { label: '선호', color: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
  fact: { label: '사실', color: 'bg-green-500/20 text-green-400 border-green-500/30' },
  rule: { label: '규칙', color: 'bg-orange-500/20 text-orange-400 border-orange-500/30' },
  insight: { label: '인사이트', color: 'bg-purple-500/20 text-purple-400 border-purple-500/30' },
  other: { label: '기타', color: 'bg-slate-500/20 text-slate-400 border-slate-500/30' },
};

const sourceLabels: Record<PersonalizationItem['source'], string> = {
  chat: '챗봇',
  manual: '직접 입력',
  agent: 'Agent',
};

export function PersonalizationPanel({
  items,
  onAddItem,
  onUpdateItem,
  onDeleteItem,
}: PersonalizationPanelProps) {
  const [newContent, setNewContent] = useState('');
  const [newCategory, setNewCategory] = useState<PersonalizationItem['category']>('other');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState('');
  const [filterCategory, setFilterCategory] = useState<PersonalizationItem['category'] | 'all'>('all');

  const handleAdd = () => {
    if (!newContent.trim()) return;
    onAddItem({
      content: newContent.trim(),
      category: newCategory,
      source: 'manual',
    });
    setNewContent('');
    setNewCategory('other');
  };

  const handleStartEdit = (item: PersonalizationItem) => {
    setEditingId(item.id);
    setEditContent(item.content);
  };

  const handleSaveEdit = () => {
    if (editingId && editContent.trim()) {
      onUpdateItem(editingId, editContent.trim());
    }
    setEditingId(null);
    setEditContent('');
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditContent('');
  };

  const filteredItems = filterCategory === 'all'
    ? items
    : items.filter(item => item.category === filterCategory);

  const sortedItems = [...filteredItems].sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
  );

  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-6">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-white">개인화 정보</h2>
        <p className="text-sm text-slate-400">
          나에 대한 정보를 저장합니다. 추후 Knowledge로 임베딩되어 Agent가 활용합니다.
        </p>
      </div>

      {/* Add New Item */}
      <div className="mb-6 p-4 bg-slate-700/50 rounded-lg">
        <div className="flex gap-3 mb-3">
          <textarea
            value={newContent}
            onChange={(e) => setNewContent(e.target.value)}
            placeholder="새로운 정보를 입력하세요 (예: '나는 아침에 커피를 마시는 것을 좋아한다')"
            className="flex-1 px-3 py-2 bg-slate-600 border border-slate-500 rounded-lg text-white text-sm resize-none focus:outline-none focus:border-blue-500"
            rows={2}
          />
        </div>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">카테고리:</span>
            <select
              value={newCategory}
              onChange={(e) => setNewCategory(e.target.value as PersonalizationItem['category'])}
              className="px-2 py-1 bg-slate-600 border border-slate-500 rounded text-sm text-white focus:outline-none focus:border-blue-500"
            >
              {Object.entries(categoryConfig).map(([key, { label }]) => (
                <option key={key} value={key}>{label}</option>
              ))}
            </select>
          </div>
          <button
            onClick={handleAdd}
            disabled={!newContent.trim()}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            추가
          </button>
        </div>
      </div>

      {/* Filter */}
      <div className="flex items-center gap-2 mb-4">
        <span className="text-xs text-slate-400">필터:</span>
        <button
          onClick={() => setFilterCategory('all')}
          className={`px-2 py-1 text-xs rounded transition-colors ${
            filterCategory === 'all'
              ? 'bg-blue-600 text-white'
              : 'bg-slate-700 text-slate-400 hover:text-white'
          }`}
        >
          전체 ({items.length})
        </button>
        {Object.entries(categoryConfig).map(([key, { label }]) => {
          const count = items.filter(i => i.category === key).length;
          if (count === 0) return null;
          return (
            <button
              key={key}
              onClick={() => setFilterCategory(key as PersonalizationItem['category'])}
              className={`px-2 py-1 text-xs rounded transition-colors ${
                filterCategory === key
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-700 text-slate-400 hover:text-white'
              }`}
            >
              {label} ({count})
            </button>
          );
        })}
      </div>

      {/* Items List */}
      <div className="space-y-2 max-h-[400px] overflow-y-auto">
        {sortedItems.length === 0 ? (
          <div className="text-center py-8 text-slate-500 text-sm">
            {filterCategory === 'all'
              ? '저장된 정보가 없습니다. 위에서 새로운 정보를 추가하세요.'
              : '해당 카테고리에 저장된 정보가 없습니다.'}
          </div>
        ) : (
          sortedItems.map(item => (
            <div
              key={item.id}
              className="p-3 bg-slate-700/50 rounded-lg border border-slate-600 hover:border-slate-500 transition-colors"
            >
              {editingId === item.id ? (
                <div className="space-y-2">
                  <textarea
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-600 border border-slate-500 rounded-lg text-white text-sm resize-none focus:outline-none focus:border-blue-500"
                    rows={2}
                    autoFocus
                  />
                  <div className="flex justify-end gap-2">
                    <button
                      onClick={handleCancelEdit}
                      className="px-3 py-1 text-xs text-slate-400 hover:text-white transition-colors"
                    >
                      취소
                    </button>
                    <button
                      onClick={handleSaveEdit}
                      className="px-3 py-1 text-xs bg-blue-600 hover:bg-blue-500 text-white rounded transition-colors"
                    >
                      저장
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm text-white flex-1">{item.content}</p>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleStartEdit(item)}
                        className="p-1 text-slate-400 hover:text-white transition-colors"
                        title="수정"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                      </button>
                      <button
                        onClick={() => onDeleteItem(item.id)}
                        className="p-1 text-slate-400 hover:text-red-400 transition-colors"
                        title="삭제"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 mt-2">
                    <span className={`px-1.5 py-0.5 text-xs rounded border ${categoryConfig[item.category].color}`}>
                      {categoryConfig[item.category].label}
                    </span>
                    <span className="text-xs text-slate-500">
                      {sourceLabels[item.source]}
                    </span>
                    <span className="text-xs text-slate-500">
                      {new Date(item.createdAt).toLocaleDateString('ko-KR')}
                    </span>
                  </div>
                </>
              )}
            </div>
          ))
        )}
      </div>

      {/* Export Button */}
      {items.length > 0 && (
        <div className="mt-4 pt-4 border-t border-slate-700">
          <button
            onClick={() => {
              const data = items.map(i => `[${categoryConfig[i.category].label}] ${i.content}`).join('\n');
              navigator.clipboard.writeText(data);
            }}
            className="text-xs text-slate-400 hover:text-white transition-colors"
          >
            전체 복사 (임베딩용)
          </button>
        </div>
      )}
    </div>
  );
}
