import { useMemo } from 'react';
import { useAgentStore } from '../stores';
import type { Agent } from '../types';

/**
 * Custom hook to get all agents (backend + custom) with memoization
 * to prevent infinite re-renders
 */
export function useAllAgents(): Agent[] {
  const agents = useAgentStore((state) => state.agents);
  const customAgents = useAgentStore((state) => state.customAgents);

  return useMemo(() => {
    const agentIds = new Set(agents.map((a) => a.id));
    const customAgentsFiltered = customAgents
      .filter((ca) => ca.isActive && !agentIds.has(ca.id))
      .map((ca) => ({
        id: ca.id,
        name: ca.name,
        type: ca.type,
        thinkingMode: 'idle' as const,
        currentTask: null,
        constraints: ca.constraints || [],
        lastActivity: ca.updatedAt,
        isActive: ca.isActive,
      }));

    return [...agents, ...customAgentsFiltered];
  }, [agents, customAgents]);
}
