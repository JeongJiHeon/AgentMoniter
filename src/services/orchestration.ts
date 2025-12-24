import { callLLM } from '../utils/llmApi';
import type { LLMConfig, Agent, Task } from '../types';
import type { ChatMessage } from '../types';

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
   * Task를 분석하여 적절한 Agent를 선택
   */
  async selectAgentForTask(task: Task, availableAgents: Agent[]): Promise<string | null> {
    if (availableAgents.length === 0) {
      console.log('[Orchestration] No available agents');
      return null;
    }

    try {
      // Agent 목록 요약 생성
      const agentSummary = availableAgents.map(agent => ({
        id: agent.id,
        name: agent.name,
        type: agent.type,
        isActive: agent.isActive,
        currentTask: agent.currentTask,
      }));

      const prompt = `다음 Task를 분석하여 가장 적합한 Agent를 선택해주세요.

Task 정보:
- 제목: ${task.title}
- 설명: ${task.description}
- 태그: ${task.tags.join(', ')}
- 우선순위: ${task.priority}
- 출처: ${task.source}

사용 가능한 Agent 목록:
${JSON.stringify(agentSummary, null, 2)}

다음 형식의 JSON으로 응답해주세요:
\`\`\`json
{
  "agentId": "선택한 Agent의 ID",
  "reason": "선택 이유 (한 줄)"
}
\`\`\`

중요:
- Task의 내용과 Agent의 type/name이 가장 관련성이 높은 Agent를 선택하세요
- 현재 작업 중이지 않은 Agent를 우선적으로 선택하되, 모든 Agent가 작업 중이면 가장 적합한 Agent를 선택하세요
- 적합한 Agent가 없으면 agentId를 null로 설정하세요`;

      const messages: ChatMessage[] = [
        {
          id: 'system',
          role: 'system',
          content: 'You are an orchestration agent that selects the most appropriate agent for a given task. Always respond with valid JSON only.',
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
        return null;
      }

      const result = JSON.parse(jsonText);

      if (!result.agentId || result.agentId === 'null') {
        console.log('[Orchestration] No suitable agent found');
        return null;
      }

      // 선택된 Agent가 실제로 존재하는지 확인
      const selectedAgent = availableAgents.find(a => a.id === result.agentId);
      if (!selectedAgent) {
        console.error(`[Orchestration] Selected agent ${result.agentId} not found`);
        return null;
      }

      console.log(`[Orchestration] Selected agent: ${selectedAgent.name} (${result.reason})`);
      return result.agentId;
    } catch (error) {
      console.error('[Orchestration] Error selecting agent:', error);
      return null;
    }
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

