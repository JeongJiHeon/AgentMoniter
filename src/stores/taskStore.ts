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

  // Bulk operations
  clearAllTasks: () => void;
  deleteCompletedTasks: () => void;
  deleteCancelledTasks: () => void;
  deleteTasksByStatus: (status: string) => void;
  clearAllLogs: () => void;
  clearTaskLogs: (taskId: string) => void;

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
  setAgentLogs: (logs: AgentLog[]) => void;
  getTaskLogs: (taskId: string) => AgentLog[];

  // Task graph
  taskGraphs: Record<string, any>;
  setTaskGraph: (taskId: string, graph: any) => void;
  getTaskGraph: (taskId: string) => any;

  // Agent memory
  agentMemories: Record<string, { memories: any[]; stats: any }>;
  setAgentMemory: (agentId: string, memories: any[], stats: any) => void;
  getAgentMemory: (agentId: string) => { memories: any[]; stats: any } | undefined;
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
    taskGraphs: {},
    agentMemories: {},

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
        // Also clean up related data
        const filteredLogs = state.agentLogs.filter(log => log.relatedTaskId !== id);
        const filteredMessages = state.taskChatMessages.filter(msg => msg.taskId !== id);
        const filteredInteractions = state.interactions.filter(i => i.taskId !== id);
        return {
          tasks: updated,
          agentLogs: filteredLogs,
          taskChatMessages: filteredMessages,
          interactions: filteredInteractions
        };
      }),

    // Bulk operations
    clearAllTasks: () =>
      set(() => {
        saveToLocalStorage('TASKS', []);
        return {
          tasks: [],
          agentLogs: [],
          taskChatMessages: [],
          interactions: [],
          processingTaskIds: new Set()
        };
      }),

    deleteCompletedTasks: () =>
      set((state) => {
        const completedIds = state.tasks.filter(t => t.status === 'completed').map(t => t.id);
        const updated = state.tasks.filter(t => t.status !== 'completed');
        saveToLocalStorage('TASKS', updated);
        return {
          tasks: updated,
          agentLogs: state.agentLogs.filter(log => !completedIds.includes(log.relatedTaskId || '')),
          taskChatMessages: state.taskChatMessages.filter(msg => !completedIds.includes(msg.taskId)),
          interactions: state.interactions.filter(i => !completedIds.includes(i.taskId))
        };
      }),

    deleteCancelledTasks: () =>
      set((state) => {
        const cancelledIds = state.tasks.filter(t => t.status === 'cancelled').map(t => t.id);
        const updated = state.tasks.filter(t => t.status !== 'cancelled');
        saveToLocalStorage('TASKS', updated);
        return {
          tasks: updated,
          agentLogs: state.agentLogs.filter(log => !cancelledIds.includes(log.relatedTaskId || '')),
          taskChatMessages: state.taskChatMessages.filter(msg => !cancelledIds.includes(msg.taskId)),
          interactions: state.interactions.filter(i => !cancelledIds.includes(i.taskId))
        };
      }),

    deleteTasksByStatus: (status) =>
      set((state) => {
        const targetIds = state.tasks.filter(t => t.status === status).map(t => t.id);
        const updated = state.tasks.filter(t => t.status !== status);
        saveToLocalStorage('TASKS', updated);
        return {
          tasks: updated,
          agentLogs: state.agentLogs.filter(log => !targetIds.includes(log.relatedTaskId || '')),
          taskChatMessages: state.taskChatMessages.filter(msg => !targetIds.includes(msg.taskId)),
          interactions: state.interactions.filter(i => !targetIds.includes(i.taskId))
        };
      }),

    clearAllLogs: () =>
      set(() => ({
        agentLogs: []
      })),

    clearTaskLogs: (taskId) =>
      set((state) => ({
        agentLogs: state.agentLogs.filter(log => log.relatedTaskId !== taskId)
      })),

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

    setAgentLogs: (logs) =>
      set(() => ({ agentLogs: logs })),

    getTaskLogs: (taskId) =>
      get().agentLogs.filter((log) => log.relatedTaskId === taskId),

    // Task graph
    setTaskGraph: (taskId, graph) =>
      set((state) => ({
        taskGraphs: { ...state.taskGraphs, [taskId]: graph }
      })),

    getTaskGraph: (taskId) =>
      get().taskGraphs[taskId] || null,

    // Agent memory
    setAgentMemory: (agentId, memories, stats) =>
      set((state) => ({
        agentMemories: {
          ...state.agentMemories,
          [agentId]: { memories, stats }
        }
      })),

    getAgentMemory: (agentId) =>
      get().agentMemories[agentId],
  };
});
