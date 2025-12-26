import { create } from 'zustand';
import type { ChatMessage, PersonalizationItem } from '../types';
import { loadFromLocalStorage, saveToLocalStorage } from '../utils/localStorage';

interface ChatState {
  // State
  chatMessages: ChatMessage[];
  personalizationItems: PersonalizationItem[];

  // Actions
  addChatMessage: (message: ChatMessage) => void;
  clearChatMessages: () => void;

  // Personalization
  addPersonalizationItem: (item: PersonalizationItem) => void;
  updatePersonalizationItem: (id: string, content: string) => void;
  deletePersonalizationItem: (id: string) => void;
}

export const useChatStore = create<ChatState>((set) => {
  const savedPersonalization = loadFromLocalStorage<PersonalizationItem[]>('PERSONALIZATION');

  return {
    // Initial State
    chatMessages: [],
    personalizationItems: savedPersonalization || [],

    // Actions
    addChatMessage: (message) =>
      set((state) => ({
        chatMessages: [...state.chatMessages, message],
      })),

    clearChatMessages: () => set({ chatMessages: [] }),

    // Personalization
    addPersonalizationItem: (item) =>
      set((state) => {
        const updated = [...state.personalizationItems, item];
        saveToLocalStorage('PERSONALIZATION', updated);
        return { personalizationItems: updated };
      }),

    updatePersonalizationItem: (id, content) =>
      set((state) => {
        const updated = state.personalizationItems.map((item) =>
          item.id === id ? { ...item, content, updatedAt: new Date() } : item
        );
        saveToLocalStorage('PERSONALIZATION', updated);
        return { personalizationItems: updated };
      }),

    deletePersonalizationItem: (id) =>
      set((state) => {
        const updated = state.personalizationItems.filter((item) => item.id !== id);
        saveToLocalStorage('PERSONALIZATION', updated);
        return { personalizationItems: updated };
      }),
  };
});
