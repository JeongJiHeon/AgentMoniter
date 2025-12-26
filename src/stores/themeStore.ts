import { create } from 'zustand';
import { loadFromLocalStorage, saveToLocalStorage } from '../utils/localStorage';

type Theme = 'dark' | 'light';

interface ThemeState {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
}

export const useThemeStore = create<ThemeState>((set) => ({
  theme: (loadFromLocalStorage<Theme>('THEME') || 'dark'),

  setTheme: (theme) => {
    saveToLocalStorage('THEME', theme);
    document.documentElement.classList.toggle('dark', theme === 'dark');
    set({ theme });
  },

  toggleTheme: () =>
    set((state) => {
      const newTheme = state.theme === 'dark' ? 'light' : 'dark';
      saveToLocalStorage('THEME', newTheme);
      document.documentElement.classList.toggle('dark', newTheme === 'dark');
      return { theme: newTheme };
    }),
}));
