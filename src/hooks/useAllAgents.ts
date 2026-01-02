import { useMemo } from 'react';
import { useAgentStore } from '../stores';
import type { Agent } from '../types';

/**
 * Custom hook to get all agents (backend + custom) with memoization
 * to prevent infinite re-renders
 *
 * Agent merging logic:
 * 1. Backend agents (from WebSocket) are used as base
 * 2. Custom agents (from settings) provide configuration (isActive = enabled)
 * 3. When merging, we use configuration isActive (enabled status) from settings
 */
export function useAllAgents(): Agent[] {
  const agents = useAgentStore((state) => state.agents);
  const customAgents = useAgentStore((state) => state.customAgents);

  return useMemo(() => {
    // Create a map of custom agents for quick lookup
    const customAgentMap = new Map(customAgents.map(ca => [ca.id, ca]));

    // Process backend agents - merge with custom agent config if exists
    const mergedAgents = agents.map((agent) => {
      const customConfig = customAgentMap.get(agent.id);
      if (customConfig) {
        // Use isActive from configuration (enabled status)
        return {
          ...agent,
          isActive: customConfig.isActive,
        };
      }
      return agent;
    });

    // Add custom agents that don't exist in backend agents
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

    return [...mergedAgents, ...customAgentsFiltered];
  }, [agents, customAgents]);
}
