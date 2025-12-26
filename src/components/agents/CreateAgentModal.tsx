import { useState, useEffect } from 'react';
import type { CustomAgentConfig, MCPService, LLMConfig } from '../../types';
import { generateAgentConfig } from '../../utils/agentGenerator';

interface CreateAgentModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreateAgent: (config: Omit<CustomAgentConfig, 'id' | 'createdAt' | 'updatedAt'>) => void;
  availableMCPs: MCPService[];
  llmConfig: LLMConfig;
}

export function CreateAgentModal({
  isOpen,
  onClose,
  onCreateAgent,
  availableMCPs,
  llmConfig,
}: CreateAgentModalProps) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [type, setType] = useState('general');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [constraints, setConstraints] = useState<string[]>([]);
  const [newConstraint, setNewConstraint] = useState('');
  const [selectedMCPs, setSelectedMCPs] = useState<string[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [generationSuccess, setGenerationSuccess] = useState(false);
  const [autoGenerate, setAutoGenerate] = useState(true); // 맞춤 생성 토글

  const agentTypes = [
    { value: 'general', label: '범용', description: '다양한 작업을 수행하는 범용 Agent' },
    { value: 'research', label: '리서치', description: '정보 수집 및 분석 전문' },
    { value: 'writing', label: '작성', description: '문서 작성 및 편집 전문' },
    { value: 'coding', label: '코딩', description: '코드 작성 및 리뷰 전문' },
    { value: 'data', label: '데이터', description: '데이터 분석 및 처리 전문' },
    { value: 'custom', label: '커스텀', description: '완전히 사용자 정의' },
  ];

  // 모달이 닫힐 때 상태 초기화
  useEffect(() => {
    if (!isOpen) {
      // 모달이 닫힌 후 상태 초기화
      const timer = setTimeout(() => {
        setName('');
        setDescription('');
        setType('general');
        setSystemPrompt('');
        setConstraints([]);
        setSelectedMCPs([]);
        setGenerationError(null);
        setGenerationSuccess(false);
        setIsGenerating(false);
        setAutoGenerate(true);
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [isOpen]);

  const handleAddConstraint = () => {
    if (newConstraint.trim() && !constraints.includes(newConstraint.trim())) {
      setConstraints(prev => [...prev, newConstraint.trim()]);
      setNewConstraint('');
    }
  };

  const handleRemoveConstraint = (constraint: string) => {
    setConstraints(prev => prev.filter(c => c !== constraint));
  };

  const handleToggleMCP = (mcpId: string) => {
    setSelectedMCPs(prev =>
      prev.includes(mcpId)
        ? prev.filter(id => id !== mcpId)
        : [...prev, mcpId]
    );
  };

  const handleGenerateConfig = async () => {
    if (!name.trim() || !description.trim()) {
      setGenerationError('이름과 설명을 모두 입력해주세요.');
      return;
    }

    setIsGenerating(true);
    setGenerationError(null);

    try {
      const mcpNames = availableMCPs.map(mcp => mcp.name);
      const generatedConfig = await generateAgentConfig(
        name.trim(),
        description.trim(),
        llmConfig,
        mcpNames
      );

      // 생성된 설정을 폼에 적용
      setType(generatedConfig.type);
      setSystemPrompt(generatedConfig.systemPrompt);
      setConstraints(generatedConfig.constraints);

      // 추천된 MCP 서비스 선택
      const recommendedMCPIds = availableMCPs
        .filter(mcp => generatedConfig.recommendedMCPs.includes(mcp.name))
        .map(mcp => mcp.id);
      setSelectedMCPs(recommendedMCPIds);

      setGenerationError(null);
      setGenerationSuccess(true);
      
      // 성공 메시지 3초 후 자동 제거
      setTimeout(() => setGenerationSuccess(false), 3000);
    } catch (error) {
      console.error('Agent 설정 생성 실패:', error);
      setGenerationError(
        error instanceof Error
          ? error.message
          : 'Agent 설정 생성 중 오류가 발생했습니다.'
      );
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCreate = () => {
    if (!name.trim()) return;

    onCreateAgent({
      name: name.trim(),
      description: description.trim(),
      type,
      systemPrompt: systemPrompt.trim(),
      constraints,
      allowedMCPs: selectedMCPs,
      isActive: true,
    });

    // Reset form
    setName('');
    setDescription('');
    setType('general');
    setSystemPrompt('');
    setConstraints([]);
    setSelectedMCPs([]);
    setGenerationError(null);
    setGenerationSuccess(false);
    setIsGenerating(false);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-slate-800 rounded-xl border border-slate-700 w-full max-w-2xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700">
          <h2 className="text-lg font-semibold text-white">새 Agent 생성</h2>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6 overflow-y-auto max-h-[calc(90vh-130px)]">
          {/* Basic Info */}
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Agent 이름 *
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
                placeholder="예: 리서치 도우미"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                설명
              </label>
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
                placeholder="Agent가 수행하는 역할에 대한 간단한 설명"
              />
              
              {/* AI 맞춤 생성 토글 - 설명 바로 아래 */}
              <div className="mt-2 flex items-center gap-2">
                <button
                  onClick={() => setAutoGenerate(!autoGenerate)}
                  className={`relative w-9 h-5 rounded-full transition-colors ${
                    autoGenerate ? 'bg-purple-600' : 'bg-slate-600'
                  }`}
                >
                  <span
                    className={`absolute top-0.5 w-4 h-4 bg-white rounded-full transition-transform ${
                      autoGenerate ? 'left-[18px]' : 'left-0.5'
                    }`}
                  />
                </button>
                <span className="text-sm text-slate-400">AI 맞춤 생성</span>
                {autoGenerate && (
                  <button
                    onClick={handleGenerateConfig}
                    disabled={!name.trim() || !description.trim() || isGenerating}
                    className="ml-auto px-3 py-1 bg-purple-600 hover:bg-purple-500 text-white text-sm rounded disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-1.5"
                  >
                    {isGenerating ? (
                      <>
                        <svg className="animate-spin h-3 w-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        <span>생성 중...</span>
                      </>
                    ) : (
                      <>
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                        <span>생성</span>
                      </>
                    )}
                  </button>
                )}
              </div>
              
              {generationError && (
                <p className="mt-2 text-sm text-red-400 flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  {generationError}
                </p>
              )}
              {generationSuccess && (
                <p className="mt-2 text-sm text-green-400 flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  설정이 자동 생성되었습니다!
                </p>
              )}
            </div>
          </div>

          {/* Agent Type */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Agent 유형
            </label>
            <div className="grid grid-cols-3 gap-2">
              {agentTypes.map(({ value, label, description }) => (
                <button
                  key={value}
                  onClick={() => setType(value)}
                  className={`p-3 rounded-lg border text-left transition-all ${
                    type === value
                      ? 'border-blue-500 bg-blue-500/10'
                      : 'border-slate-600 bg-slate-700 hover:border-slate-500'
                  }`}
                >
                  <div className="font-medium text-white text-sm">{label}</div>
                  <div className="text-xs text-slate-400 mt-0.5">{description}</div>
                </button>
              ))}
            </div>
          </div>

          {/* System Prompt */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              시스템 프롬프트
            </label>
            <textarea
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500 resize-none"
              rows={4}
              placeholder="Agent의 행동 방식과 목표를 정의하는 시스템 프롬프트"
            />
          </div>

          {/* Constraints */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              제약 조건
            </label>
            <div className="flex gap-2 mb-2">
              <input
                type="text"
                value={newConstraint}
                onChange={(e) => setNewConstraint(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAddConstraint()}
                className="flex-1 px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                placeholder="새 제약 조건 입력 (Enter로 추가)"
              />
              <button
                onClick={handleAddConstraint}
                disabled={!newConstraint.trim()}
                className="px-4 py-2 bg-slate-600 hover:bg-slate-500 text-white text-sm rounded-lg disabled:opacity-50 transition-colors"
              >
                추가
              </button>
            </div>
            {constraints.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {constraints.map((constraint, index) => (
                  <span
                    key={index}
                    className="px-2 py-1 bg-red-500/10 border border-red-500/30 rounded text-sm text-red-400 flex items-center gap-1"
                  >
                    {constraint}
                    <button
                      onClick={() => handleRemoveConstraint(constraint)}
                      className="hover:text-red-300"
                    >
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Allowed MCPs */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              허용된 MCP 서비스
            </label>
            {availableMCPs.length === 0 ? (
              <p className="text-sm text-slate-500">설정된 MCP 서비스가 없습니다.</p>
            ) : (
              <div className="grid grid-cols-2 gap-2">
                {availableMCPs.map(mcp => (
                  <button
                    key={mcp.id}
                    onClick={() => handleToggleMCP(mcp.id)}
                    className={`p-3 rounded-lg border text-left transition-all ${
                      selectedMCPs.includes(mcp.id)
                        ? 'border-blue-500 bg-blue-500/10'
                        : 'border-slate-600 bg-slate-700 hover:border-slate-500'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-white text-sm">{mcp.name}</span>
                      {selectedMCPs.includes(mcp.id) && (
                        <svg className="w-4 h-4 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      )}
                    </div>
                    <p className="text-xs text-slate-400 mt-0.5">{mcp.type}</p>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-slate-700">
          <button
            onClick={onClose}
            className="px-4 py-2 text-slate-400 hover:text-white transition-colors"
          >
            취소
          </button>
          <button
            onClick={handleCreate}
            disabled={!name.trim()}
            className="px-6 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Agent 생성
          </button>
        </div>
      </div>
    </div>
  );
}
