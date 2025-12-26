import { create } from 'zustand';
import type { Agent, CustomAgentConfig } from '../types';
import { loadFromLocalStorage, saveToLocalStorage } from '../utils/localStorage';

interface AgentState {
  // State
  agents: Agent[];
  selectedAgent: Agent | null;
  customAgents: CustomAgentConfig[];

  // Actions
  setAgents: (agents: Agent[]) => void;
  updateAgent: (id: string, updates: Partial<Agent>) => void;
  addAgent: (agent: Agent) => void;
  setSelectedAgent: (agent: Agent | null) => void;

  // Custom Agents
  addCustomAgent: (config: CustomAgentConfig) => void;
  updateCustomAgent: (id: string, updates: Partial<CustomAgentConfig>) => void;
  deleteCustomAgent: (id: string) => void;
}

export const useAgentStore = create<AgentState>((set) => ({
  // Initial State
  agents: [],
  selectedAgent: null,
  customAgents: loadFromLocalStorage<CustomAgentConfig[]>('CUSTOM_AGENTS') || [],

  // Actions
  setAgents: (agents) => set({ agents }),

  updateAgent: (id, updates) =>
    set((state) => ({
      agents: state.agents.map((agent) =>
        agent.id === id ? { ...agent, ...updates } : agent
      ),
    })),

  addAgent: (agent) =>
    set((state) => {
      const existingIndex = state.agents.findIndex((a) => a.id === agent.id);
      if (existingIndex >= 0) {
        const updated = [...state.agents];
        updated[existingIndex] = agent;
        return { agents: updated };
      }
      return { agents: [...state.agents, agent] };
    }),

  setSelectedAgent: (agent) => set({ selectedAgent: agent }),

  // Custom Agents
  addCustomAgent: (config) =>
    set((state) => {
      const updated = [...state.customAgents, config];
      saveToLocalStorage('CUSTOM_AGENTS', updated);
      return { customAgents: updated };
    }),

  updateCustomAgent: (id, updates) =>
    set((state) => {
      const updated = state.customAgents.map((agent) =>
        agent.id === id ? { ...agent, ...updates, updatedAt: new Date() } : agent
      );
      saveToLocalStorage('CUSTOM_AGENTS', updated);
      return { customAgents: updated };
    }),

  deleteCustomAgent: (id) =>
    set((state) => {
      const updated = state.customAgents.filter((agent) => agent.id !== id);
      saveToLocalStorage('CUSTOM_AGENTS', updated);
      return { customAgents: updated };
    }),
}));
