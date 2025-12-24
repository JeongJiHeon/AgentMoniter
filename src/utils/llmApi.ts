import type { LLMConfig, ChatMessage } from '../types';

export interface LLMStreamCallbacks {
  onToken?: (token: string) => void;
  onComplete?: (fullText: string) => void;
  onError?: (error: Error) => void;
}

/**
 * LLM API 호출 유틸리티
 */
export async function callLLM(
  config: LLMConfig,
  messages: ChatMessage[],
  callbacks?: LLMStreamCallbacks
): Promise<string> {
  if (!config.apiKey) {
    throw new Error(`${config.provider} API 키가 설정되지 않았습니다. 설정 탭에서 API 키를 입력해주세요.`);
  }

  switch (config.provider) {
    case 'anthropic':
      return callAnthropicAPI(config, messages, callbacks);
    case 'openai':
    case 'azure':
    case 'local':
      return callOpenAIAPI(config, messages, callbacks);
    case 'google':
      return callGoogleAPI(config, messages, callbacks);
    default:
      throw new Error(`지원하지 않는 provider: ${config.provider}`);
  }
}

/**
 * Anthropic API 호출
 */
async function callAnthropicAPI(
  config: LLMConfig,
  messages: ChatMessage[],
  callbacks?: LLMStreamCallbacks
): Promise<string> {
  const apiUrl = config.baseUrl || 'https://api.anthropic.com/v1/messages';

  // ChatMessage를 Anthropic 형식으로 변환
  const formattedMessages = messages
    .filter(m => m.role !== 'system')
    .map(m => ({
      role: m.role === 'assistant' ? 'assistant' : 'user',
      content: m.content,
    }));

  try {
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': config.apiKey!,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: config.model,
        messages: formattedMessages,
        max_tokens: config.maxTokens,
        temperature: config.temperature,
        stream: false, // 스트리밍은 추후 구현
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: { message: response.statusText } }));
      throw new Error(errorData.error?.message || `API 호출 실패: ${response.status}`);
    }

    const data = await response.json();
    const content = data.content?.[0]?.text || '';

    callbacks?.onComplete?.(content);
    return content;
  } catch (error) {
    const err = error instanceof Error ? error : new Error(String(error));
    callbacks?.onError?.(err);
    throw err;
  }
}

/**
 * OpenAI API 호출 (Azure, Local 포함)
 */
async function callOpenAIAPI(
  config: LLMConfig,
  messages: ChatMessage[],
  callbacks?: LLMStreamCallbacks
): Promise<string> {
  // 개발 환경에서는 Vite 프록시 사용 (CORS 우회)
  const isDev = import.meta.env.DEV;
  let apiUrl: string;

  if (isDev && config.baseUrl && config.baseUrl.includes('api.platform.a15t.com')) {
    // Vite 프록시를 통한 호출
    apiUrl = '/api/llm/chat/completions';
  } else {
    // 직접 API 호출 또는 다른 베이스 URL
    apiUrl = config.baseUrl || 'https://api.openai.com/v1';
    if (!apiUrl.includes('/chat/completions')) {
      apiUrl = apiUrl.endsWith('/') ? `${apiUrl}chat/completions` : `${apiUrl}/chat/completions`;
    }
  }

  // ChatMessage를 OpenAI 형식으로 변환
  const formattedMessages = messages.map(m => ({
    role: m.role,
    content: m.content,
  }));

  console.log('[LLM API Request]', {
    url: apiUrl,
    model: config.model,
    messageCount: formattedMessages.length,
  });

  try {
    const response = await fetch(apiUrl, {
      method: 'POST',
      mode: 'cors',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${config.apiKey}`,
      },
      body: JSON.stringify({
        model: config.model,
        messages: formattedMessages,
        max_completion_tokens: config.maxTokens,
        temperature: config.temperature,
        stream: false,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      let errorMessage = `API 호출 실패 (${response.status})`;

      try {
        const errorData = JSON.parse(errorText);
        errorMessage = errorData.error?.message || errorData.message || errorMessage;
      } catch {
        errorMessage = errorText || errorMessage;
      }

      console.error('[LLM API Error]', {
        status: response.status,
        url: apiUrl,
        error: errorMessage,
      });

      throw new Error(errorMessage);
    }

    const data = await response.json();
    const content = data.choices?.[0]?.message?.content || '';

    if (!content) {
      console.warn('[LLM API Warning] Empty response:', data);
    }

    callbacks?.onComplete?.(content);
    return content;
  } catch (error) {
    console.error('[LLM API Exception]', error);
    const err = error instanceof Error ? error : new Error(String(error));
    callbacks?.onError?.(err);
    throw err;
  }
}

/**
 * Google Gemini API 호출
 */
async function callGoogleAPI(
  config: LLMConfig,
  messages: ChatMessage[],
  callbacks?: LLMStreamCallbacks
): Promise<string> {
  const apiUrl = config.baseUrl || `https://generativelanguage.googleapis.com/v1beta/models/${config.model}:generateContent`;

  // ChatMessage를 Gemini 형식으로 변환
  const contents = messages.map(m => ({
    role: m.role === 'assistant' ? 'model' : 'user',
    parts: [{ text: m.content }],
  }));

  try {
    const response = await fetch(`${apiUrl}?key=${config.apiKey}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        contents,
        generationConfig: {
          temperature: config.temperature,
          maxOutputTokens: config.maxTokens,
        },
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: { message: response.statusText } }));
      throw new Error(errorData.error?.message || `API 호출 실패: ${response.status}`);
    }

    const data = await response.json();
    const content = data.candidates?.[0]?.content?.parts?.[0]?.text || '';

    callbacks?.onComplete?.(content);
    return content;
  } catch (error) {
    const err = error instanceof Error ? error : new Error(String(error));
    callbacks?.onError?.(err);
    throw err;
  }
}
