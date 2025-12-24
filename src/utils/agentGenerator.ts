import type { LLMConfig } from '../types';
import { callLLM } from './llmApi';

export interface GeneratedAgentConfig {
  type: string;
  systemPrompt: string;
  constraints: string[];
  recommendedMCPs: string[];
}

/**
 * LLM을 사용하여 Agent 설정 자동 생성
 */
export async function generateAgentConfig(
  name: string,
  description: string,
  llmConfig: LLMConfig,
  availableMCPs: string[]
): Promise<GeneratedAgentConfig> {
  const prompt = `
다음 정보를 바탕으로 Agent Monitor 시스템에서 사용할 Agent 설정을 생성해주세요.

**Agent 이름**: ${name}
**Agent 설명**: ${description}

**사용 가능한 MCP 서비스**: ${availableMCPs.join(', ')}

다음 형식의 JSON으로 응답해주세요:

\`\`\`json
{
  "type": "general|research|writing|coding|data|custom 중 하나",
  "systemPrompt": "Agent의 행동 방식과 목표를 정의하는 상세한 시스템 프롬프트 (3-5문장)",
  "constraints": [
    "제약 조건 1",
    "제약 조건 2",
    "제약 조건 3"
  ],
  "recommendedMCPs": ["추천 MCP 서비스 이름들"]
}
\`\`\`

**Agent 유형 가이드**:
- general: 다양한 작업 수행
- research: 정보 수집 및 분석
- writing: 문서 작성 및 편집
- coding: 코드 작성 및 리뷰
- data: 데이터 분석 및 처리
- custom: 특수한 목적

**제약 조건 예시**:
- "승인 없이 외부 API 호출 금지"
- "민감한 정보는 로그에 기록하지 않음"
- "작업 시작 전 반드시 실행 계획 제시"

JSON만 응답하고 다른 설명은 추가하지 마세요.
`;

  const messages = [
    {
      id: 'system',
      role: 'system' as const,
      content: 'You are an AI assistant specialized in creating Agent configurations. Always respond with valid JSON only.',
      timestamp: new Date(),
    },
    {
      id: 'user',
      role: 'user' as const,
      content: prompt,
      timestamp: new Date(),
    },
  ];

  try {
    const response = await callLLM(llmConfig, messages);

    // JSON 추출
    let jsonText = '';
    
    // 먼저 코드 블록에서 JSON 추출 시도
    const codeBlockMatch = response.match(/```(?:json)?\s*([\s\S]*?)\s*```/);
    if (codeBlockMatch) {
      jsonText = codeBlockMatch[1].trim();
    } else {
      // 코드 블록이 없으면 중괄호로 감싸진 JSON 찾기
      const jsonMatch = response.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        jsonText = jsonMatch[0];
      }
    }

    if (!jsonText) {
      throw new Error('LLM 응답에서 JSON을 찾을 수 없습니다. 응답: ' + response.substring(0, 200));
    }

    const config = JSON.parse(jsonText);

    // 검증
    if (!config.type || !config.systemPrompt || !Array.isArray(config.constraints)) {
      throw new Error('유효하지 않은 Agent 설정입니다.');
    }

    return {
      type: config.type,
      systemPrompt: config.systemPrompt,
      constraints: config.constraints,
      recommendedMCPs: config.recommendedMCPs || [],
    };
  } catch (error) {
    console.error('[Agent Generator Error]', error);
    throw new Error(`Agent 설정 생성 실패: ${error instanceof Error ? error.message : String(error)}`);
  }
}
