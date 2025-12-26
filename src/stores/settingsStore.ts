import { create } from 'zustand';
import type { AppSettings, MCPService, LLMConfig, ExternalAPI } from '../types';
import { loadFromLocalStorage, saveToLocalStorage } from '../utils/localStorage';
import { DEFAULT_APP_SETTINGS } from '../constants';

interface SettingsState {
  // State
  settings: AppSettings;

  // Actions
  updateSettings: (updates: Partial<AppSettings>) => void;
  updateLLMConfig: (config: Partial<LLMConfig>) => void;
  updateMCPService: (id: string, updates: Partial<MCPService>) => void;
  addMCPService: (service: MCPService) => void;
  removeMCPService: (id: string) => void;
  updateExternalAPI: (id: string, updates: Partial<ExternalAPI>) => void;
}

export const useSettingsStore = create<SettingsState>((set) => {
  // Load from localStorage or use defaults
  const savedSettings = loadFromLocalStorage<AppSettings>('SETTINGS');

  return {
    // Initial State
    settings: savedSettings || DEFAULT_APP_SETTINGS,

    // Actions
    updateSettings: (updates) =>
      set((state) => {
        const updated = { ...state.settings, ...updates };
        saveToLocalStorage('SETTINGS', updated);
        return { settings: updated };
      }),

    updateLLMConfig: (config) =>
      set((state) => {
        const updated = {
          ...state.settings,
          llmConfig: { ...state.settings.llmConfig, ...config },
        };
        saveToLocalStorage('SETTINGS', updated);
        return { settings: updated };
      }),

    updateMCPService: (id, updates) =>
      set((state) => {
        const updated = {
          ...state.settings,
          mcpServices: state.settings.mcpServices.map((service) =>
            service.id === id ? { ...service, ...updates } : service
          ),
        };
        saveToLocalStorage('SETTINGS', updated);
        return { settings: updated };
      }),

    addMCPService: (service) =>
      set((state) => {
        const updated = {
          ...state.settings,
          mcpServices: [...state.settings.mcpServices, service],
        };
        saveToLocalStorage('SETTINGS', updated);
        return { settings: updated };
      }),

    removeMCPService: (id) =>
      set((state) => {
        const updated = {
          ...state.settings,
          mcpServices: state.settings.mcpServices.filter((s) => s.id !== id),
        };
        saveToLocalStorage('SETTINGS', updated);
        return { settings: updated };
      }),

    updateExternalAPI: (id, updates) =>
      set((state) => {
        const updated = {
          ...state.settings,
          externalAPIs: state.settings.externalAPIs.map((api) =>
            api.id === id ? { ...api, ...updates } : api
          ),
        };
        saveToLocalStorage('SETTINGS', updated);
        return { settings: updated };
      }),
  };
});
