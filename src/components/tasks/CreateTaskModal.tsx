import { useState } from 'react';
import type { CreateTaskInput, TaskPriority } from '../../types/task';

interface CreateTaskModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreateTask: (task: CreateTaskInput) => void;
  defaultAutoAssign?: boolean;
}

export function CreateTaskModal({ isOpen, onClose, onCreateTask, defaultAutoAssign = false }: CreateTaskModalProps) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState<TaskPriority>('medium');
  const [tags, setTags] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [autoAssign, setAutoAssign] = useState(defaultAutoAssign);

  if (!isOpen) return null;

  const handleSubmit = () => {
    if (!title.trim()) return;

    onCreateTask({
      title: title.trim(),
      description: description.trim(),
      priority,
      tags: tags.split(',').map(t => t.trim()).filter(Boolean),
      dueDate: dueDate ? new Date(dueDate) : undefined,
      source: 'manual',
      autoAssign,
    });

    // Reset form
    setTitle('');
    setDescription('');
    setPriority('medium');
    setTags('');
    setDueDate('');
    setAutoAssign(defaultAutoAssign);
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-slate-800 rounded-xl border border-slate-700 w-full max-w-md">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700">
          <h2 className="text-lg font-semibold text-white">새 Task 생성</h2>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              제목 *
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
              placeholder="Task 제목을 입력하세요"
              onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              설명
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500 resize-none"
              rows={3}
              placeholder="Task에 대한 상세 설명"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                우선순위
              </label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value as TaskPriority)}
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
              >
                <option value="low">낮음</option>
                <option value="medium">보통</option>
                <option value="high">높음</option>
                <option value="urgent">긴급</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                마감일
              </label>
              <input
                type="date"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              태그 (쉼표로 구분)
            </label>
            <input
              type="text"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
              placeholder="예: 긴급, 개발, 버그"
            />
          </div>
        </div>

        <div className="flex items-center justify-between p-3 bg-slate-700/50 border border-slate-600 rounded-lg">
          <div>
            <label className="text-sm font-medium text-slate-300">자동 할당</label>
            <p className="text-xs text-slate-400 mt-1">Orchestration Agent가 자동으로 적절한 Agent를 선택합니다</p>
          </div>
          <button
            type="button"
            onClick={() => setAutoAssign(!autoAssign)}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              autoAssign ? 'bg-blue-600' : 'bg-slate-600'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                autoAssign ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-slate-700">
          <button
            onClick={onClose}
            className="px-4 py-2 text-slate-400 hover:text-white transition-colors"
          >
            취소
          </button>
          <button
            onClick={handleSubmit}
            disabled={!title.trim()}
            className="px-6 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            생성
          </button>
        </div>
      </div>
    </div>
  );
}

