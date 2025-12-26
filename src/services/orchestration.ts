import { callLLM } from '../utils/llmApi';
import type { LLMConfig, Agent, Task } from '../types';
import type { ChatMessage } from '../types';

export interface SelectedAgent {
  agentId: string;
  agentName: string;
  reason: string;
  order: number;
}

export interface OrchestrationPlan {
  agents: SelectedAgent[];
  needsUserInput: boolean;
  inputPrompt?: string;
}

/**
 * Orchestration Agent 서비스
 * Task를 분석하여 적절한 Agent를 선택하는 역할
 */
export class OrchestrationService {
  private llmConfig: LLMConfig;

  constructor(llmConfig: LLMConfig) {
    this.llmConfig = llmConfig;
  }

  /**
   * Task를 분석하여 여러 Agent를 선택 (멀티-에이전트 Planning)
   */
  async selectAgentsForTask(task: Task, availableAgents: Agent[]): Promise<OrchestrationPlan> {
    if (availableAgents.length === 0) {
      console.log('[Orchestration] No available agents');
      return { agents: [], needsUserInput: false };
    }

    try {
      const agentSummary = availableAgents.map(agent => ({
        id: agent.id,
        name: agent.name,
        type: agent.type,
      }));

      const prompt = `다음 Task를 분석하여 필요한 Agent들을 순서대로 선택해주세요.

Task 정보:
- 제목: ${task.title}
- 설명: ${task.description}
- 출처: ${task.source}

사용 가능한 Agent 목록:
${JSON.stringify(agentSummary, null, 2)}

다음 형식의 JSON으로 응답해주세요:
\`\`\`json
{
  "agents": [
    {"agentId": "ID1", "reason": "이 Agent가 필요한 이유", "order": 1},
    {"agentId": "ID2", "reason": "이 Agent가 필요한 이유", "order": 2}
  ],
  "needsUserInput": true/false,
  "inputPrompt": "사용자에게 물어볼 질문 (needsUserInput이 true일 때)"
}
\`\`\`

중요:
- Task를 완료하는데 필요한 모든 Agent를 실행 순서대로 나열하세요
- 예: "점심메뉴 추천하고 예약해줘" → 메뉴 추천 Agent(1) → 예약 Agent(2)
- 사용자 선택이 필요한 경우 needsUserInput을 true로 설정하고 inputPrompt에 질문을 작성하세요
- 적합한 Agent가 없으면 agents를 빈 배열로 설정하세요`;

      const messages: ChatMessage[] = [
        {
          id: 'system',
          role: 'system',
          content: 'You are an orchestration agent that plans multi-agent workflows. Always respond with valid JSON only.',
          timestamp: new Date(),
        },
        {
          id: 'user',
          role: 'user',
          content: prompt,
          timestamp: new Date(),
        },
      ];

      const response = await callLLM(this.llmConfig, messages);

      // JSON 추출
      let jsonText = '';
      const codeBlockMatch = response.match(/```(?:json)?\s*([\s\S]*?)\s*```/);
      if (codeBlockMatch) {
        jsonText = codeBlockMatch[1].trim();
      } else {
        const jsonMatch = response.match(/\{[\s\S]*\}/);
        if (jsonMatch) {
          jsonText = jsonMatch[0];
        }
      }

      if (!jsonText) {
        console.error('[Orchestration] Failed to extract JSON from response');
        return { agents: [], needsUserInput: false };
      }

      const result = JSON.parse(jsonText);

      // 선택된 Agent들 검증
      const validAgents: SelectedAgent[] = [];
      for (const item of result.agents || []) {
        const agent = availableAgents.find(a => a.id === item.agentId);
        if (agent) {
          validAgents.push({
            agentId: agent.id,
            agentName: agent.name,
            reason: item.reason || '',
            order: item.order || validAgents.length + 1,
          });
        }
      }

      // 순서대로 정렬
      validAgents.sort((a, b) => a.order - b.order);

      console.log(`[Orchestration] Selected ${validAgents.length} agents:`, validAgents.map(a => a.agentName));
      
      return {
        agents: validAgents,
        needsUserInput: result.needsUserInput || false,
        inputPrompt: result.inputPrompt,
      };
    } catch (error) {
      console.error('[Orchestration] Error selecting agents:', error);
      return { agents: [], needsUserInput: false };
    }
  }

  /**
   * Task를 분석하여 단일 Agent를 선택 (기존 호환성 유지)
   */
  async selectAgentForTask(task: Task, availableAgents: Agent[]): Promise<string | null> {
    const plan = await this.selectAgentsForTask(task, availableAgents);
    if (plan.agents.length > 0) {
      return plan.agents[0].agentId;
    }
    return null;
  }

  /**
   * Task의 우선순위와 내용을 분석하여 자동 할당 여부 결정
   */
  shouldAutoAssign(task: Task): boolean {
    // 긴급하거나 높은 우선순위의 Task는 자동 할당
    if (task.priority === 'urgent' || task.priority === 'high') {
      return true;
    }

    // Slack에서 온 Task는 자동 할당
    if (task.source === 'slack') {
      return true;
    }

    // 기본적으로는 자동 할당하지 않음
    return false;
  }
}

