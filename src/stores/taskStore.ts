import { create } from 'zustand';
import type { Task, Interaction, TaskChatMessage, AgentLog } from '../types';
import { loadFromLocalStorage, saveToLocalStorage } from '../utils/localStorage';

interface TaskState {
  // State
  tasks: Task[];
  autoAssignMode: 'global' | 'manual';
  processingTaskIds: Set<string>;

  // Interactions & Logs
  interactions: Interaction[];
  taskChatMessages: TaskChatMessage[];
  agentLogs: AgentLog[];

  // Actions
  setTasks: (tasks: Task[]) => void;
  addTask: (task: Task) => void;
  updateTask: (id: string, updates: Partial<Task>) => void;
  deleteTask: (id: string) => void;

  // Processing tracking
  markTaskAsProcessing: (id: string) => void;
  unmarkTaskAsProcessing: (id: string) => void;
  isTaskProcessing: (id: string) => boolean;

  // Auto-assign mode
  setAutoAssignMode: (mode: 'global' | 'manual') => void;

  // Interactions
  addInteraction: (interaction: Interaction) => void;
  updateInteraction: (id: string, updates: Partial<Interaction>) => void;

  // Chat messages
  addTaskChatMessage: (message: TaskChatMessage) => void;
  getTaskChatMessages: (taskId: string) => TaskChatMessage[];

  // Agent logs
  addAgentLog: (log: AgentLog) => void;
  getTaskLogs: (taskId: string) => AgentLog[];
}

export const useTaskStore = create<TaskState>((set, get) => {
  // Load initial tasks from localStorage
  const savedTasks = loadFromLocalStorage<Task[]>('TASKS');
  const initialTasks = savedTasks
    ? savedTasks.map((t) => ({
        ...t,
        createdAt: new Date(t.createdAt),
        updatedAt: new Date(t.updatedAt),
        completedAt: t.completedAt ? new Date(t.completedAt) : undefined,
      }))
    : [];

  const savedAutoAssignMode = loadFromLocalStorage<'global' | 'manual'>('AUTO_ASSIGN_MODE');

  return {
    // Initial State
    tasks: initialTasks,
    autoAssignMode: savedAutoAssignMode || 'manual',
    processingTaskIds: new Set(),
    interactions: [],
    taskChatMessages: [],
    agentLogs: [],

    // Actions
    setTasks: (tasks) => {
      saveToLocalStorage('TASKS', tasks);
      set({ tasks });
    },

    addTask: (task) =>
      set((state) => {
        // Prevent duplicates
        if (state.tasks.find((t) => t.id === task.id)) {
          return state;
        }
        const updated = [...state.tasks, task];
        saveToLocalStorage('TASKS', updated);
        return { tasks: updated };
      }),

    updateTask: (id, updates) =>
      set((state) => {
        const updated = state.tasks.map((task) =>
          task.id === id ? { ...task, ...updates, updatedAt: new Date() } : task
        );
        saveToLocalStorage('TASKS', updated);
        return { tasks: updated };
      }),

    deleteTask: (id) =>
      set((state) => {
        const updated = state.tasks.filter((task) => task.id !== id);
        saveToLocalStorage('TASKS', updated);
        return { tasks: updated };
      }),

    // Processing tracking
    markTaskAsProcessing: (id) =>
      set((state) => {
        const newSet = new Set(state.processingTaskIds);
        newSet.add(id);
        return { processingTaskIds: newSet };
      }),

    unmarkTaskAsProcessing: (id) =>
      set((state) => {
        const newSet = new Set(state.processingTaskIds);
        newSet.delete(id);
        return { processingTaskIds: newSet };
      }),

    isTaskProcessing: (id) => get().processingTaskIds.has(id),

    // Auto-assign mode
    setAutoAssignMode: (mode) => {
      saveToLocalStorage('AUTO_ASSIGN_MODE', mode);
      set({ autoAssignMode: mode });
    },

    // Interactions
    addInteraction: (interaction) =>
      set((state) => ({
        interactions: [...state.interactions, interaction],
      })),

    updateInteraction: (id, updates) =>
      set((state) => ({
        interactions: state.interactions.map((i) =>
          i.id === id ? { ...i, ...updates } : i
        ),
      })),

    // Chat messages
    addTaskChatMessage: (message) =>
      set((state) => {
        // Prevent duplicates
        const existingIndex = state.taskChatMessages.findIndex(
          (msg) => msg.id === message.id
        );
        if (existingIndex >= 0) {
          const updated = [...state.taskChatMessages];
          updated[existingIndex] = message;
          return { taskChatMessages: updated };
        }
        return { taskChatMessages: [...state.taskChatMessages, message] };
      }),

    getTaskChatMessages: (taskId) =>
      get().taskChatMessages.filter((msg) => msg.taskId === taskId),

    // Agent logs
    addAgentLog: (log) =>
      set((state) => {
        // Prevent duplicates by ID
        if (state.agentLogs.find((l) => l.id === log.id)) {
          return state;
        }
        return { agentLogs: [...state.agentLogs, log] };
      }),

    getTaskLogs: (taskId) =>
      get().agentLogs.filter((log) => log.relatedTaskId === taskId),
  };
});
