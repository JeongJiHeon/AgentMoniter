import { useState } from 'react';
import type { CreateTaskInput } from '../../types/task';
import { callLLM } from '../../utils/llmApi';
import type { ChatMessage, LLMConfig } from '../../types';

interface AnalyzeMCPMessagesModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreateTasks: (tasks: CreateTaskInput[]) => void;
  availableMCPs: Array<{ id: string; type: string; name: string; status: string }>;
  llmConfig: LLMConfig;
}

export function AnalyzeMCPMessagesModal({
  isOpen,
  onClose,
  onCreateTasks,
  availableMCPs,
  llmConfig,
}: AnalyzeMCPMessagesModalProps) {
  const [selectedMCP, setSelectedMCP] = useState<string>('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [messages, setMessages] = useState<Array<{ id: string; content: string; timestamp: string }>>([]);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const connectedMCPs = availableMCPs.filter(mcp => mcp.status === 'connected');

  const handleFetchMessages = async () => {
    if (!selectedMCP) return;

    setIsAnalyzing(true);
    setError(null);

    try {
      // TODO: 실제 MCP API를 통해 메시지 가져오기
      // 현재는 모의 데이터 사용
      const mockMessages = [
        {
          id: '1',
          content: '프로젝트 문서를 업데이트해주세요',
          timestamp: new Date().toISOString(),
        },
        {
          id: '2',
          content: '코드 리뷰가 필요합니다',
          timestamp: new Date().toISOString(),
        },
      ];

      setMessages(mockMessages);
    } catch (err) {
      setError(err instanceof Error ? err.message : '메시지를 가져오는 중 오류가 발생했습니다.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleAnalyze = async () => {
    if (messages.length === 0) return;

    setIsAnalyzing(true);
    setError(null);

    try {
      const messagesText = messages.map((m, idx) => `메시지 ${idx + 1}: ${m.content}`).join('\n');

      const prompt = `다음 메시지들을 분석하여 Task로 변환해주세요. 각 메시지에서 해야 할 작업을 추출하여 Task로 만들어주세요.

${messagesText}

다음 형식의 JSON 배열로 응답해주세요:

\`\`\`json
[
  {
    "title": "Task 제목",
    "description": "Task 상세 설명",
    "priority": "low|medium|high|urgent",
    "tags": ["태그1", "태그2"]
  }
]
\`\`\`

중요: 실제로 해야 할 작업이 명확한 경우만 Task로 변환하세요.`;

      const extractionMessages: ChatMessage[] = [
        {
          id: 'system',
          role: 'system',
          content: 'You are an AI assistant specialized in extracting tasks from messages. Always respond with valid JSON only.',
          timestamp: new Date(),
        },
        {
          id: 'user',
          role: 'user',
          content: prompt,
          timestamp: new Date(),
        },
      ];

      const response = await callLLM(llmConfig, extractionMessages);

      // JSON 추출
      let jsonText = '';
      const codeBlockMatch = response.match(/```(?:json)?\s*([\s\S]*?)\s*```/);
      if (codeBlockMatch) {
        jsonText = codeBlockMatch[1].trim();
      } else {
        const jsonMatch = response.match(/\[[\s\S]*\]/);
        if (jsonMatch) {
          jsonText = jsonMatch[0];
        }
      }

      if (!jsonText) {
        throw new Error('LLM 응답에서 JSON을 찾을 수 없습니다.');
      }

      const tasks = JSON.parse(jsonText);

      if (!Array.isArray(tasks) || tasks.length === 0) {
        throw new Error('추출된 Task가 없습니다.');
      }

      const validTasks: CreateTaskInput[] = tasks
        .filter((task: any) => task.title && task.description)
        .map((task: any) => ({
          title: task.title.trim(),
          description: task.description.trim(),
          priority: task.priority || 'medium',
          tags: task.tags || [],
          source: selectedMCP.includes('slack') ? 'slack' : selectedMCP.includes('confluence') ? 'confluence' : 'other',
        }));

      if (validTasks.length > 0) {
        onCreateTasks(validTasks);
        setMessages([]);
        setSelectedMCP('');
      } else {
        throw new Error('유효한 Task를 찾을 수 없습니다.');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '메시지 분석 중 오류가 발생했습니다.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-slate-800 rounded-xl border border-slate-700 w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700">
          <h2 className="text-lg font-semibold text-white">MCP 메시지 분석</h2>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-6 space-y-4 overflow-y-auto flex-1">
          {connectedMCPs.length === 0 ? (
            <div className="text-center py-8 text-slate-500">
              <p>연결된 MCP 서비스가 없습니다.</p>
              <p className="text-sm mt-2">설정에서 MCP 서비스를 연결해주세요.</p>
            </div>
          ) : (
            <>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  MCP 서비스 선택
                </label>
                <select
                  value={selectedMCP}
                  onChange={(e) => {
                    setSelectedMCP(e.target.value);
                    setMessages([]);
                  }}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:border-blue-500"
                >
                  <option value="">서비스를 선택하세요</option>
                  {connectedMCPs.map(mcp => (
                    <option key={mcp.id} value={mcp.id}>
                      {mcp.name} ({mcp.type})
                    </option>
                  ))}
                </select>
              </div>

              {selectedMCP && (
                <div>
                  <button
                    onClick={handleFetchMessages}
                    disabled={isAnalyzing}
                    className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg disabled:opacity-50 transition-colors"
                  >
                    {isAnalyzing ? '메시지 가져오는 중...' : '메시지 가져오기'}
                  </button>
                </div>
              )}

              {messages.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-slate-300 mb-2">
                    가져온 메시지 ({messages.length}개)
                  </h3>
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {messages.map(msg => (
                      <div
                        key={msg.id}
                        className="p-3 bg-slate-700 rounded-lg border border-slate-600"
                      >
                        <p className="text-sm text-slate-200">{msg.content}</p>
                        <p className="text-xs text-slate-500 mt-1">
                          {new Date(msg.timestamp).toLocaleString('ko-KR')}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {error && (
                <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
                  <p className="text-sm text-red-400">{error}</p>
                </div>
              )}
            </>
          )}
        </div>

        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-slate-700">
          <button
            onClick={onClose}
            className="px-4 py-2 text-slate-400 hover:text-white transition-colors"
          >
            취소
          </button>
          <button
            onClick={handleAnalyze}
            disabled={messages.length === 0 || isAnalyzing}
            className="px-6 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isAnalyzing ? '분석 중...' : 'Task로 변환'}
          </button>
        </div>
      </div>
    </div>
  );
}

