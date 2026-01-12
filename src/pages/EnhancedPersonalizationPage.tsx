import { useState, useMemo } from 'react';
import { useChatStore } from '../stores';
import { Brain, Star, Lightbulb, Book, Sparkles, Plus, Edit2, Trash2, Copy, Filter } from 'lucide-react';
import type { PersonalizationItem } from '../types';

const categoryConfig: Record<PersonalizationItem['category'], {
  label: string;
  color: string;
  icon: React.ComponentType<{ className?: string }>;
}> = {
  preference: {
    label: 'Preference',
    color: 'bg-cyan-500/20 text-cyan-300 border-cyan-400/30',
    icon: Star
  },
  fact: {
    label: 'Fact',
    color: 'bg-emerald-500/20 text-emerald-300 border-emerald-400/30',
    icon: Book
  },
  rule: {
    label: 'Rule',
    color: 'bg-amber-500/20 text-amber-300 border-amber-400/30',
    icon: Lightbulb
  },
  insight: {
    label: 'Insight',
    color: 'bg-magenta-500/20 text-magenta-300 border-magenta-400/30',
    icon: Sparkles
  },
  other: {
    label: 'Other',
    color: 'bg-gray-500/20 text-gray-300 border-gray-400/30',
    icon: Brain
  },
};

const sourceLabels: Record<PersonalizationItem['source'], string> = {
  chat: 'Chat',
  manual: 'Manual',
  agent: 'Agent',
};

export function EnhancedPersonalizationPage() {
  const { personalizationItems, addPersonalizationItem, updatePersonalizationItem, deletePersonalizationItem } = useChatStore();

  const [newContent, setNewContent] = useState('');
  const [newCategory, setNewCategory] = useState<PersonalizationItem['category']>('other');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState('');
  const [filterCategory, setFilterCategory] = useState<PersonalizationItem['category'] | 'all'>('all');

  const handleAdd = () => {
    if (!newContent.trim()) return;
    const newItem: PersonalizationItem = {
      content: newContent.trim(),
      category: newCategory,
      source: 'manual',
      id: crypto.randomUUID(),
      createdAt: new Date(),
      updatedAt: new Date(),
    };
    addPersonalizationItem(newItem);
    setNewContent('');
    setNewCategory('other');
  };

  const handleStartEdit = (item: PersonalizationItem) => {
    setEditingId(item.id);
    setEditContent(item.content);
  };

  const handleSaveEdit = () => {
    if (editingId && editContent.trim()) {
      updatePersonalizationItem(editingId, editContent.trim());
    }
    setEditingId(null);
    setEditContent('');
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditContent('');
  };

  const handleExport = () => {
    const data = personalizationItems.map(i => `[${categoryConfig[i.category].label}] ${i.content}`).join('\n');
    navigator.clipboard.writeText(data);
  };

  const filteredItems = filterCategory === 'all'
    ? personalizationItems
    : personalizationItems.filter(item => item.category === filterCategory);

  const sortedItems = [...filteredItems].sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
  );

  // Category counts
  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = { all: personalizationItems.length };
    personalizationItems.forEach(item => {
      counts[item.category] = (counts[item.category] || 0) + 1;
    });
    return counts;
  }, [personalizationItems]);

  return (
    <div className="h-screen bg-[#0a0e1a] text-gray-100 overflow-hidden font-mono">
      {/* Background grid effect */}
      <div className="fixed inset-0 bg-[linear-gradient(rgba(34,211,238,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(34,211,238,0.03)_1px,transparent_1px)] bg-[size:40px_40px] pointer-events-none" />

      {/* Scanline effect */}
      <div className="fixed inset-0 bg-[linear-gradient(transparent_50%,rgba(0,217,255,0.02)_50%)] bg-[size:100%_4px] pointer-events-none animate-scanline" />

      <div className="relative z-10 h-full flex flex-col overflow-hidden">
        {/* Header */}
        <div className="border-b border-cyan-400/10 bg-gradient-to-r from-[#0d1117]/95 to-[#0a0e1a]/95 backdrop-blur-xl">
          <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-cyan-400/50 to-transparent" />
          <div className="px-6 py-4">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-xl font-bold bg-gradient-to-r from-cyan-400 to-cyan-300 bg-clip-text text-transparent tracking-tight">
                  KNOWLEDGE BASE
                </h1>
                <p className="text-xs text-gray-500 mt-0.5 tracking-wider">Personalization & Memory System</p>
              </div>

              <div className="flex items-center gap-3">
                {/* Stats */}
                <div className="flex items-center gap-4 px-4 py-2 bg-cyan-500/10 border border-cyan-400/20 rounded-lg">
                  <div className="flex items-center gap-2">
                    <Brain className="w-4 h-4 text-cyan-400" />
                    <span className="text-sm font-bold text-cyan-300 tabular-nums">{personalizationItems.length}</span>
                    <span className="text-xs text-gray-500">items</span>
                  </div>
                </div>

                {/* Export Button */}
                {personalizationItems.length > 0 && (
                  <button
                    onClick={handleExport}
                    className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-magenta-500/20 to-magenta-600/20 hover:from-magenta-500/30 hover:to-magenta-600/30 text-magenta-300 rounded-lg text-sm font-medium transition-all border border-magenta-400/30"
                  >
                    <Copy className="w-4 h-4" />
                    Export All
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 grid grid-cols-12 gap-4 p-6 overflow-hidden">
          {/* Left Panel - Add New */}
          <div className="col-span-4 flex flex-col gap-4 overflow-hidden">
            <div className="bg-gradient-to-br from-[#1a1f2e]/50 to-[#0d1117]/50 border border-cyan-400/10 rounded-xl backdrop-blur-xl p-4">
              <div className="flex items-center gap-2 mb-4">
                <Plus className="w-4 h-4 text-cyan-400" />
                <h2 className="text-sm font-bold text-cyan-300 tracking-wider uppercase">Add Knowledge</h2>
              </div>

              <div className="space-y-3">
                <div>
                  <label className="text-xs text-gray-500 uppercase mb-2 block">Content</label>
                  <textarea
                    value={newContent}
                    onChange={(e) => setNewContent(e.target.value)}
                    placeholder="Enter information about yourself..."
                    className="w-full px-3 py-2 bg-[#1a1f2e]/80 border border-cyan-400/20 rounded-lg text-gray-300 text-sm resize-none focus:outline-none focus:border-cyan-400/50 focus:ring-1 focus:ring-cyan-400/30 transition-all placeholder-gray-600"
                    rows={4}
                  />
                </div>

                <div>
                  <label className="text-xs text-gray-500 uppercase mb-2 block">Category</label>
                  <select
                    value={newCategory}
                    onChange={(e) => setNewCategory(e.target.value as PersonalizationItem['category'])}
                    className="w-full px-3 py-2 bg-[#1a1f2e]/80 border border-cyan-400/20 rounded-lg text-gray-300 text-sm focus:outline-none focus:border-cyan-400/50 focus:ring-1 focus:ring-cyan-400/30 transition-all"
                  >
                    {Object.entries(categoryConfig).map(([key, { label }]) => (
                      <option key={key} value={key}>{label}</option>
                    ))}
                  </select>
                </div>

                <button
                  onClick={handleAdd}
                  disabled={!newContent.trim()}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-cyan-500 to-cyan-600 hover:from-cyan-400 hover:to-cyan-500 text-white rounded-lg text-sm font-medium transition-all shadow-lg shadow-cyan-500/20 hover:shadow-cyan-500/40 border border-cyan-400/50 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-none"
                >
                  <Plus className="w-4 h-4" />
                  Add to Knowledge Base
                </button>
              </div>
            </div>

            {/* Category Filter */}
            <div className="bg-gradient-to-br from-[#1a1f2e]/50 to-[#0d1117]/50 border border-cyan-400/10 rounded-xl backdrop-blur-xl p-4">
              <div className="flex items-center gap-2 mb-3">
                <Filter className="w-4 h-4 text-cyan-400" />
                <h2 className="text-sm font-bold text-cyan-300 tracking-wider uppercase">Filter</h2>
              </div>

              <div className="space-y-2">
                <button
                  onClick={() => setFilterCategory('all')}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-all ${
                    filterCategory === 'all'
                      ? 'bg-cyan-500/20 border border-cyan-400/30 text-cyan-300'
                      : 'bg-gray-800/30 border border-gray-700/30 text-gray-400 hover:border-gray-600/50'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span>All Categories</span>
                    <span className="text-xs tabular-nums">{categoryCounts.all}</span>
                  </div>
                </button>

                {Object.entries(categoryConfig).map(([key, { label, icon: Icon, color }]) => {
                  const count = categoryCounts[key] || 0;
                  if (count === 0) return null;

                  return (
                    <button
                      key={key}
                      onClick={() => setFilterCategory(key as PersonalizationItem['category'])}
                      className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-all ${
                        filterCategory === key
                          ? color.replace('/20', '/30').replace('text-', 'bg-').split(' ')[0] + ' border ' + color.split(' ')[2] + ' ' + color.split(' ')[1]
                          : 'bg-gray-800/30 border border-gray-700/30 text-gray-400 hover:border-gray-600/50'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Icon className="w-3 h-3" />
                          <span>{label}</span>
                        </div>
                        <span className="text-xs tabular-nums">{count}</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Right Panel - Items List */}
          <div className="col-span-8 bg-gradient-to-br from-[#1a1f2e]/50 to-[#0d1117]/50 border border-cyan-400/10 rounded-xl backdrop-blur-xl overflow-hidden flex flex-col">
            <div className="px-4 py-3 border-b border-cyan-400/10">
              <h2 className="text-sm font-bold text-cyan-300 tracking-wider uppercase">
                {filterCategory === 'all' ? 'All Knowledge' : categoryConfig[filterCategory as PersonalizationItem['category']].label}
                {' '}({sortedItems.length})
              </h2>
            </div>

            <div className="flex-1 overflow-y-auto p-4">
              {sortedItems.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-gray-600">
                  <Brain className="w-16 h-16 mb-4 opacity-20" />
                  <p className="text-sm mb-2">No knowledge items</p>
                  <p className="text-xs text-gray-700">
                    {filterCategory === 'all'
                      ? 'Add your first knowledge item to get started'
                      : 'No items in this category'}
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {sortedItems.map(item => (
                    <div
                      key={item.id}
                      className="p-4 bg-gradient-to-br from-gray-800/30 to-gray-900/30 border border-gray-700/30 rounded-lg hover:border-cyan-400/30 transition-all group"
                    >
                      {editingId === item.id ? (
                        <div className="space-y-3">
                          <textarea
                            value={editContent}
                            onChange={(e) => setEditContent(e.target.value)}
                            className="w-full px-3 py-2 bg-[#1a1f2e]/80 border border-cyan-400/20 rounded-lg text-gray-300 text-sm resize-none focus:outline-none focus:border-cyan-400/50 focus:ring-1 focus:ring-cyan-400/30 transition-all"
                            rows={3}
                            autoFocus
                          />
                          <div className="flex justify-end gap-2">
                            <button
                              onClick={handleCancelEdit}
                              className="px-3 py-1.5 text-xs text-gray-400 hover:text-white transition-colors"
                            >
                              Cancel
                            </button>
                            <button
                              onClick={handleSaveEdit}
                              className="px-3 py-1.5 text-xs bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 rounded border border-cyan-400/30 transition-colors"
                            >
                              Save
                            </button>
                          </div>
                        </div>
                      ) : (
                        <>
                          <div className="flex items-start justify-between gap-3 mb-3">
                            <p className="text-sm text-gray-200 flex-1 leading-relaxed">{item.content}</p>
                            <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                              <button
                                onClick={() => handleStartEdit(item)}
                                className="p-1.5 hover:bg-cyan-500/10 rounded border border-transparent hover:border-cyan-400/30 transition-colors text-gray-400 hover:text-cyan-400"
                                title="Edit"
                              >
                                <Edit2 className="w-3.5 h-3.5" />
                              </button>
                              <button
                                onClick={() => deletePersonalizationItem(item.id)}
                                className="p-1.5 hover:bg-red-500/10 rounded border border-transparent hover:border-red-400/30 transition-colors text-gray-400 hover:text-red-400"
                                title="Delete"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          </div>

                          <div className="flex items-center gap-2 flex-wrap">
                            {(() => {
                              const config = categoryConfig[item.category];
                              const Icon = config.icon;
                              return (
                                <span className={`flex items-center gap-1 px-2 py-0.5 text-[10px] rounded border ${config.color} uppercase font-medium`}>
                                  <Icon className="w-2.5 h-2.5" />
                                  {config.label}
                                </span>
                              );
                            })()}
                            <span className="px-2 py-0.5 text-[10px] rounded border bg-gray-700/30 border-gray-600/30 text-gray-400 uppercase">
                              {sourceLabels[item.source]}
                            </span>
                            <span className="text-[10px] text-gray-600">
                              {new Date(item.createdAt).toLocaleDateString('en-US', {
                                month: 'short',
                                day: 'numeric',
                                year: 'numeric'
                              })}
                            </span>
                          </div>
                        </>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Custom styles */}
      <style>{`
        @keyframes scanline {
          0% { transform: translateY(0); }
          100% { transform: translateY(100vh); }
        }
        .animate-scanline {
          animation: scanline 8s linear infinite;
        }

        /* Custom scrollbar */
        ::-webkit-scrollbar {
          width: 6px;
          height: 6px;
        }
        ::-webkit-scrollbar-track {
          background: rgba(17, 24, 39, 0.3);
        }
        ::-webkit-scrollbar-thumb {
          background: rgba(34, 211, 238, 0.3);
          border-radius: 3px;
        }
        ::-webkit-scrollbar-thumb:hover {
          background: rgba(34, 211, 238, 0.5);
        }
      `}</style>
    </div>
  );
}
