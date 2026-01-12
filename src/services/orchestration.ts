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

      console.log('[Orchestration] LLM Response:', response);

      // JSON 추출
      let jsonText = '';
      const codeBlockMatch = response.match(/```(?:json)?\s*([\s\S]*?)\s*```/);
      if (codeBlockMatch) {
        jsonText = codeBlockMatch[1].trim();
      } else {
        // 코드 블록이 없으면 중괄호로 시작하는 JSON 찾기
        const jsonMatch = response.match(/\{[\s\S]*\}/);
        if (jsonMatch) {
          jsonText = jsonMatch[0];
        }
      }

      if (!jsonText) {
        console.error('[Orchestration] Failed to extract JSON from response. Full response:', response);
        // JSON 추출 실패 시 폴백: 첫 번째 에이전트를 기본으로 선택
        if (availableAgents.length > 0) {
          console.log('[Orchestration] Fallback: Using first available agent');
          return {
            agents: [{
              agentId: availableAgents[0].id,
              agentName: availableAgents[0].name,
              reason: 'LLM 응답 파싱 실패로 기본 에이전트 선택',
              order: 1,
            }],
            needsUserInput: false,
          };
        }
        return { agents: [], needsUserInput: false };
      }

      let result: any;
      try {
        result = JSON.parse(jsonText);
      } catch (parseError) {
        console.error('[Orchestration] JSON parse error:', parseError);
        console.error('[Orchestration] JSON text:', jsonText);
        // JSON 파싱 실패 시 폴백
        if (availableAgents.length > 0) {
          console.log('[Orchestration] Fallback: Using first available agent (JSON parse failed)');
          return {
            agents: [{
              agentId: availableAgents[0].id,
              agentName: availableAgents[0].name,
              reason: 'JSON 파싱 실패로 기본 에이전트 선택',
              order: 1,
            }],
            needsUserInput: false,
          };
        }
        return { agents: [], needsUserInput: false };
      }

      // 선택된 Agent들 검증
      const validAgents: SelectedAgent[] = [];
      const agentsArray = result.agents || [];
      
      if (!Array.isArray(agentsArray)) {
        console.warn('[Orchestration] agents is not an array:', agentsArray);
      }

      for (const item of agentsArray) {
        if (!item || typeof item !== 'object') {
          console.warn('[Orchestration] Invalid agent item:', item);
          continue;
        }

        const agentId = item.agentId || item.id;
        if (!agentId) {
          console.warn('[Orchestration] Agent item missing agentId:', item);
          continue;
        }

        const agent = availableAgents.find(a => a.id === agentId);
        if (agent) {
          validAgents.push({
            agentId: agent.id,
            agentName: agent.name,
            reason: item.reason || '선택됨',
            order: typeof item.order === 'number' ? item.order : validAgents.length + 1,
          });
        } else {
          console.warn(`[Orchestration] Agent not found: ${agentId}`);
        }
      }

      // 순서대로 정렬
      validAgents.sort((a, b) => a.order - b.order);

      console.log(`[Orchestration] Selected ${validAgents.length} agents:`, validAgents.map(a => a.agentName));

      // 에이전트가 선택되지 않았고 사용 가능한 에이전트가 있는 경우 폴백
      if (validAgents.length === 0 && availableAgents.length > 0) {
        console.log('[Orchestration] No valid agents selected, using fallback');
        return {
          agents: [{
            agentId: availableAgents[0].id,
            agentName: availableAgents[0].name,
            reason: '에이전트 선택 실패로 기본 에이전트 사용',
            order: 1,
          }],
          needsUserInput: result.needsUserInput || false,
          inputPrompt: result.inputPrompt,
        };
      }
      
      return {
        agents: validAgents,
        needsUserInput: result.needsUserInput || false,
        inputPrompt: result.inputPrompt,
      };
    } catch (error) {
      console.error('[Orchestration] Error selecting agents:', error);
      console.error('[Orchestration] Error details:', error instanceof Error ? error.stack : error);
      
      // 에러 발생 시 폴백: 첫 번째 에이전트를 기본으로 선택
      if (availableAgents.length > 0) {
        console.log('[Orchestration] Fallback: Using first available agent (error occurred)');
        return {
          agents: [{
            agentId: availableAgents[0].id,
            agentName: availableAgents[0].name,
            reason: '에러 발생으로 기본 에이전트 선택',
            order: 1,
          }],
          needsUserInput: false,
        };
      }
      
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

