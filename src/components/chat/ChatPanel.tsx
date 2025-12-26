import { useState, useRef, useEffect } from 'react';
import type { ChatMessage, LLMConfig, PersonalizationItem } from '../../types';
import { callLLM } from '../../utils/llmApi';
import { SYSTEM_KNOWLEDGE } from '../../constants/systemKnowledge';

interface ChatPanelProps {
  llmConfig: LLMConfig;
  agentCount: number;
  mcpCount: number;
  personalizationCount: number;
  onSaveInsight?: (content: string) => void;
  onAutoSavePersonalization?: (items: Omit<PersonalizationItem, 'id' | 'createdAt' | 'updatedAt' | 'source'>[]) => void;
  externalMessages?: ChatMessage[];
  onMessagesRead?: () => void;
  onSendMessage?: (message: string) => void; // Orchestration Agent를 통한 메시지 전송
  useOrchestration?: boolean; // Orchestration Agent 사용 여부
}

export function ChatPanel({
  llmConfig,
  agentCount,
  mcpCount,
  personalizationCount,
  onSaveInsight,
  onAutoSavePersonalization,
  externalMessages = [],
  onMessagesRead,
  onSendMessage,
  useOrchestration = true, // 기본값으로 Orchestration Agent 사용
}: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [autoSaveNotification, setAutoSaveNotification] = useState<string | null>(null);
  const [unreadCount, setUnreadCount] = useState(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const lastExternalMessageCountRef = useRef(0);

  // 시스템 프롬프트 생성
  const systemPrompt = SYSTEM_KNOWLEDGE
    .replace('{provider}', llmConfig.provider)
    .replace('{model}', llmConfig.model)
    .replace('{agentCount}', String(agentCount))
    .replace('{mcpCount}', String(mcpCount))
    .replace('{personalizationCount}', String(personalizationCount));

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 외부 메시지 추가 (Agent 응답 등)
  useEffect(() => {
    if (externalMessages.length > lastExternalMessageCountRef.current) {
      const newMessages = externalMessages.slice(lastExternalMessageCountRef.current);
      setMessages(prev => [...prev, ...newMessages]);
      
      // 읽지 않은 메시지 개수 업데이트 (항상 패널이 보이므로 0으로 유지)
      setUnreadCount(0);
      onMessagesRead?.();
      
      lastExternalMessageCountRef.current = externalMessages.length;
    }
  }, [externalMessages, onMessagesRead]);

  const handleSend = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: inputValue.trim(),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      if (useOrchestration && onSendMessage) {
        // Orchestration Agent를 통한 메시지 전송
        onSendMessage(userMessage.content);
        // 응답은 externalMessages를 통해 받음
        setIsLoading(false);
      } else {
        // 기존 방식: 직접 LLM 호출
        // 시스템 프롬프트를 포함한 메시지 구성
        const systemMessage: ChatMessage = {
          id: 'system',
          role: 'system',
          content: systemPrompt,
          timestamp: new Date(),
        };

        const conversationMessages = messages.length === 0
          ? [systemMessage, userMessage]
          : [...messages, userMessage];

        // 실제 LLM API 호출
        const content = await callLLM(llmConfig, conversationMessages);

        const assistantMessage: ChatMessage = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content,
          timestamp: new Date(),
        };
        setMessages(prev => [...prev, assistantMessage]);

        // 자동으로 개인화 정보 추출 시도 (비동기로 실행, 블로킹하지 않음)
        extractPersonalizationInfo(userMessage.content, content).catch(err => {
          console.error('[ChatPanel] 개인화 정보 추출 실패:', err);
        });
        setIsLoading(false);
      }
    } catch (error) {
      const errorMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: `오류가 발생했습니다: ${error instanceof Error ? error.message : String(error)}`,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
      setIsLoading(false);
    }
  };

  const extractPersonalizationInfo = async (userMsg: string, assistantMsg: string) => {
    if (!onAutoSavePersonalization) return;

    try {
      // LLM을 사용하여 개인화 정보 추출
      const extractionPrompt = `다음 대화 내용에서 사용자의 개인화 정보(선호사항, 규칙, 선호하는 작업 방식, 언어 선호도 등)를 추출해주세요.

사용자: ${userMsg}
봇: ${assistantMsg}

다음 형식의 JSON 배열로 응답해주세요. 개인화 정보가 없으면 빈 배열 []을 반환하세요:

\`\`\`json
[
  {
    "category": "preference|fact|rule|insight|other",
    "content": "추출된 개인화 정보 내용"
  }
]
\`\`\`

카테고리 가이드:
- preference: 선호사항 (언어, 스타일, 작업 방식 등)
- fact: 사실 정보 (직업, 전문 분야 등)
- rule: 규칙이나 제약사항
- insight: 통찰이나 학습한 내용
- other: 기타 중요한 정보

중요: 개인화 정보가 명확하게 드러나지 않으면 빈 배열을 반환하세요.`;

      const extractionMessages: ChatMessage[] = [
        {
          id: 'system',
          role: 'system',
          content: 'You are an AI assistant specialized in extracting personalization information from conversations. Always respond with valid JSON only.',
          timestamp: new Date(),
        },
        {
          id: 'user',
          role: 'user',
          content: extractionPrompt,
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
        // JSON을 찾을 수 없으면 휴리스틱 방식으로 폴백
        return extractPersonalizationInfoFallback(userMsg, assistantMsg);
      }

      const items = JSON.parse(jsonText);

      if (!Array.isArray(items) || items.length === 0) {
        return;
      }

      // 유효성 검사 및 정리
      const validItems: Omit<PersonalizationItem, 'id' | 'createdAt' | 'updatedAt' | 'source'>[] = items
        .filter((item: any) => item.category && item.content && item.content.trim().length > 0)
        .map((item: any) => ({
          category: item.category as PersonalizationItem['category'],
          content: item.content.trim(),
        }));

      if (validItems.length > 0) {
        console.log('[Auto Personalization] LLM으로 추출된 정보:', validItems);
        onAutoSavePersonalization(validItems);

        // 알림 표시
        setAutoSaveNotification(`개인화 정보 ${validItems.length}개 자동 저장됨`);
        setTimeout(() => setAutoSaveNotification(null), 3000);
      }
    } catch (error) {
      console.error('[Auto Personalization] LLM 추출 실패, 휴리스틱 방식으로 폴백:', error);
      // LLM 추출 실패 시 휴리스틱 방식으로 폴백
      extractPersonalizationInfoFallback(userMsg, assistantMsg);
    }
  };

  const extractPersonalizationInfoFallback = (userMsg: string, assistantMsg: string) => {
    if (!onAutoSavePersonalization) return;

    // 간단한 휴리스틱으로 개인화 정보 추출 (폴백)
    const combinedText = `사용자: ${userMsg}\n봇: ${assistantMsg}`;
    
    // 더 많은 키워드 추가
    const personalInfoKeywords = [
      '저는', '나는', '내가', '제가', '좋아', '싫어', '선호', '항상', '자주', '전문', 
      '일해', '사용해', '원해', '원합니다', '원해요', '해주세요', '해줘', '답변', '언어',
      '한글', '영어', '스타일', '방식', '규칙', '제약', '필요', '중요'
    ];

    const hasPersonalInfo = personalInfoKeywords.some(keyword => combinedText.includes(keyword));

    if (!hasPersonalInfo) return;

    const items: Omit<PersonalizationItem, 'id' | 'createdAt' | 'updatedAt' | 'source'>[] = [];

    // 언어 선호도 패턴
    const languagePatterns = [
      /(한글|한국어|한국말|한국 언어).*?(답변|사용|쓰기|말하기|작성)/gi,
      /(영어|English|영문).*?(답변|사용|쓰기|말하기|작성)/gi,
      /(답변|사용|쓰기|말하기|작성).*?(한글|한국어|한국말|한국 언어)/gi,
      /(답변|사용|쓰기|말하기|작성).*?(영어|English|영문)/gi,
    ];

    languagePatterns.forEach(pattern => {
      const match = combinedText.match(pattern);
      if (match) {
        items.push({
          category: 'preference',
          content: match[0].trim(),
        });
      }
    });

    // "저는 ~입니다" 패턴
    const factPattern = /(저는|나는|제가|내가)\s+([^.!?\n]{5,100})(입니다|예요|에요|해요|입니다|입니다)/g;
    let match;
    while ((match = factPattern.exec(combinedText)) !== null) {
      items.push({
        category: 'fact',
        content: match[0].trim(),
      });
    }

    // "~를 좋아합니다/선호합니다" 패턴
    const preferencePattern = /([^.!?\n]{5,100})(좋아합니다|좋아해요|선호합니다|선호해요|원합니다|원해요)/g;
    while ((match = preferencePattern.exec(combinedText)) !== null) {
      items.push({
        category: 'preference',
        content: match[0].trim(),
      });
    }

    // "~해주세요/해줘" 패턴 (요청사항)
    const requestPattern = /([^.!?\n]{5,100})(해주세요|해줘|해주시면|해주시겠어요)/g;
    while ((match = requestPattern.exec(combinedText)) !== null) {
      const content = match[0].trim();
      // 언어 관련 요청인지 확인
      if (content.includes('한글') || content.includes('한국어') || content.includes('영어') || content.includes('답변')) {
        items.push({
          category: 'preference',
          content: content,
        });
      } else {
        items.push({
          category: 'rule',
          content: content,
        });
      }
    }

    // 중복 제거
    const uniqueItems = items.filter((item, index, self) =>
      index === self.findIndex(t => t.content === item.content)
    );

    if (uniqueItems.length > 0) {
      console.log('[Auto Personalization] 휴리스틱으로 추출된 정보:', uniqueItems);
      onAutoSavePersonalization(uniqueItems);

      // 알림 표시
      setAutoSaveNotification(`개인화 정보 ${uniqueItems.length}개 자동 저장됨`);
      setTimeout(() => setAutoSaveNotification(null), 3000);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSaveAsInsight = (content: string) => {
    if (onSaveInsight) {
      onSaveInsight(content);
    }
  };

  const clearChat = () => {
    setMessages([]);
  };

  return (
    <div className="h-full flex flex-col bg-slate-800">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-green-500"></div>
          <span className="text-sm font-medium text-white">LLM Chat</span>
          <span className="text-xs text-slate-500">
            ({llmConfig.provider}/{llmConfig.model})
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={clearChat}
            className="p-1 text-slate-400 hover:text-white transition-colors"
            title="대화 초기화"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
          {unreadCount > 0 && (
            <span className="px-2 py-1 bg-red-500 text-white text-xs font-bold rounded-full">
              {unreadCount > 9 ? '9+' : unreadCount}
            </span>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-slate-500 text-sm py-8">
            <p>LLM에게 질문하세요</p>
            <p className="text-xs mt-1">Shift+Enter로 줄바꿈</p>
          </div>
        )}
        {messages.map(message => (
          <div
            key={message.id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-lg px-3 py-2 ${
                message.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-700 text-slate-200'
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">{message.content}</p>
              <div className="flex items-center justify-between mt-1 gap-2">
                <span className="text-xs opacity-60">
                  {message.timestamp.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}
                </span>
                {message.role === 'assistant' && onSaveInsight && (
                  <button
                    onClick={() => handleSaveAsInsight(message.content)}
                    className="text-xs text-blue-400 hover:text-blue-300"
                    title="개인화 정보로 저장"
                  >
                    저장
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-slate-700 rounded-lg px-3 py-2">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                <div className="w-2 h-2 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                <div className="w-2 h-2 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-3 border-t border-slate-700">
        <div className="flex gap-2">
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="메시지를 입력하세요..."
            className="flex-1 px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white text-sm resize-none focus:outline-none focus:border-blue-500"
            rows={1}
            disabled={isLoading}
          />
          <button
            onClick={handleSend}
            disabled={!inputValue.trim() || isLoading}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
      </div>

      {/* Auto-save Notification */}
      {autoSaveNotification && (
        <div className="absolute top-16 left-4 bg-green-600 text-white px-4 py-2 rounded-lg shadow-lg z-50 animate-fade-in">
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            <span className="text-sm">{autoSaveNotification}</span>
          </div>
        </div>
      )}
    </div>
  );
}
