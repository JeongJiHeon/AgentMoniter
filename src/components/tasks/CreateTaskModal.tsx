/**
 * CreateTaskModal - 접근성 및 폼 유효성 검사가 강화된 Task 생성 모달
 *
 * Features:
 * - 실시간 폼 유효성 검사
 * - 접근성 (ARIA, 키보드 네비게이션)
 * - 로딩 상태 표시
 * - 에러 메시지 표시
 */

import { useState, useRef, useCallback } from 'react';
import type { CreateTaskInput, TaskPriority } from '../../types/task';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { Input, Textarea } from '../ui/Input';
import { validators, useForm } from '../ui/FormValidation';

interface CreateTaskModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreateTask: (task: CreateTaskInput) => void;
  defaultAutoAssign?: boolean;
  isLoading?: boolean;
}

export function CreateTaskModal({
  isOpen,
  onClose,
  onCreateTask,
  defaultAutoAssign = false,
  isLoading = false,
}: CreateTaskModalProps) {
  const [priority, setPriority] = useState<TaskPriority>('medium');
  const [autoAssign, setAutoAssign] = useState(defaultAutoAssign);
  const titleInputRef = useRef<HTMLInputElement>(null);

  const {
    values,
    getFieldProps,
    reset,
    validateAll,
  } = useForm({
    initialValues: {
      title: '',
      description: '',
      tags: '',
      dueDate: '',
    },
    validationRules: {
      title: [
        validators.required('제목을 입력해주세요'),
        validators.minLength(2, '제목은 2자 이상 입력해주세요'),
        validators.maxLength(100, '제목은 100자 이내로 입력해주세요'),
      ],
      description: [
        validators.maxLength(1000, '설명은 1000자 이내로 입력해주세요'),
      ],
    },
  });

  const handleSubmit = useCallback(() => {
    if (!validateAll()) return;

    onCreateTask({
      title: values.title.trim(),
      description: values.description.trim(),
      priority,
      tags: values.tags.split(',').map(t => t.trim()).filter(Boolean),
      dueDate: values.dueDate ? new Date(values.dueDate) : undefined,
      source: 'manual',
      autoAssign,
    });

    // Reset form
    reset();
    setPriority('medium');
    setAutoAssign(defaultAutoAssign);
    onClose();
  }, [validateAll, values, priority, autoAssign, defaultAutoAssign, onCreateTask, reset, onClose]);

  const handleClose = useCallback(() => {
    reset();
    setPriority('medium');
    setAutoAssign(defaultAutoAssign);
    onClose();
  }, [reset, defaultAutoAssign, onClose]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      handleSubmit();
    }
  }, [handleSubmit]);

  const titleProps = getFieldProps('title');
  const descriptionProps = getFieldProps('description');
  const tagsProps = getFieldProps('tags');
  const dueDateProps = getFieldProps('dueDate');

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="새 Task 생성"
      description="Agent에게 할당할 새로운 Task를 생성합니다"
      size="md"
      initialFocusRef={titleInputRef}
      footer={
        <div className="flex items-center justify-between">
          <p className="text-xs text-slate-500">
            <kbd className="px-1.5 py-0.5 bg-slate-700 rounded text-slate-400">Ctrl</kbd>
            {' + '}
            <kbd className="px-1.5 py-0.5 bg-slate-700 rounded text-slate-400">Enter</kbd>
            {' 로 빠른 생성'}
          </p>
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              onClick={handleClose}
              disabled={isLoading}
            >
              취소
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={!values.title.trim() || isLoading}
              isLoading={isLoading}
              loadingText="생성 중..."
            >
              생성
            </Button>
          </div>
        </div>
      }
    >
      <form onSubmit={(e) => { e.preventDefault(); handleSubmit(); }} onKeyDown={handleKeyDown}>
        <div className="space-y-4">
          {/* 제목 */}
          <Input
            ref={titleInputRef}
            label="제목"
            placeholder="Task 제목을 입력하세요"
            isRequired
            value={titleProps.value}
            onChange={titleProps.onChange}
            onBlur={titleProps.onBlur}
            error={titleProps.error}
            autoComplete="off"
          />

          {/* 설명 */}
          <Textarea
            label="설명"
            placeholder="Task에 대한 상세 설명"
            rows={3}
            value={descriptionProps.value}
            onChange={descriptionProps.onChange}
            onBlur={descriptionProps.onBlur}
            error={descriptionProps.error}
            hint="선택 사항입니다"
          />

          {/* 우선순위 & 마감일 */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label
                htmlFor="priority"
                className="block text-sm font-medium text-slate-300 mb-2"
              >
                우선순위
              </label>
              <select
                id="priority"
                value={priority}
                onChange={(e) => setPriority(e.target.value as TaskPriority)}
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                aria-describedby="priority-hint"
              >
                <option value="low">낮음</option>
                <option value="medium">보통</option>
                <option value="high">높음</option>
                <option value="urgent">긴급</option>
              </select>
              <p id="priority-hint" className="sr-only">
                Task의 우선순위를 선택하세요
              </p>
            </div>

            <div>
              <label
                htmlFor="dueDate"
                className="block text-sm font-medium text-slate-300 mb-2"
              >
                마감일
              </label>
              <input
                id="dueDate"
                type="date"
                value={dueDateProps.value}
                onChange={dueDateProps.onChange}
                min={new Date().toISOString().split('T')[0]}
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-colors"
                aria-describedby="dueDate-hint"
              />
              <p id="dueDate-hint" className="sr-only">
                Task의 마감일을 선택하세요 (선택 사항)
              </p>
            </div>
          </div>

          {/* 태그 */}
          <Input
            label="태그"
            placeholder="예: 긴급, 개발, 버그"
            hint="쉼표로 구분하여 입력하세요"
            value={tagsProps.value}
            onChange={tagsProps.onChange}
            onBlur={tagsProps.onBlur}
            autoComplete="off"
          />

          {/* 자동 할당 토글 */}
          <div
            className="flex items-center justify-between p-4 bg-slate-700/50 border border-slate-600 rounded-lg"
            role="group"
            aria-labelledby="auto-assign-label"
          >
            <div>
              <p id="auto-assign-label" className="text-sm font-medium text-slate-300">
                자동 할당
              </p>
              <p className="text-xs text-slate-400 mt-1">
                Orchestration Agent가 자동으로 적절한 Agent를 선택합니다
              </p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={autoAssign}
              aria-labelledby="auto-assign-label"
              onClick={() => setAutoAssign(!autoAssign)}
              className={`
                relative inline-flex h-6 w-11 items-center rounded-full transition-colors
                focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-slate-800
                ${autoAssign ? 'bg-blue-600' : 'bg-slate-600'}
              `}
            >
              <span className="sr-only">
                {autoAssign ? '자동 할당 켜짐' : '자동 할당 꺼짐'}
              </span>
              <span
                aria-hidden="true"
                className={`
                  inline-block h-4 w-4 transform rounded-full bg-white transition-transform
                  ${autoAssign ? 'translate-x-6' : 'translate-x-1'}
                `}
              />
            </button>
          </div>
        </div>
      </form>
    </Modal>
  );
}

export default CreateTaskModal;
