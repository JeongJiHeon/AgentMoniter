import { create } from 'zustand';
import type { Ticket, ApprovalRequest } from '../types';
import { loadFromLocalStorage, saveToLocalStorage } from '../utils/localStorage';

interface TicketState {
  // State
  tickets: Ticket[];
  approvalQueue: ApprovalRequest[];

  // Actions
  setTickets: (tickets: Ticket[]) => void;
  addTicket: (ticket: Ticket) => void;
  updateTicket: (id: string, updates: Partial<Ticket>) => void;
  deleteTicket: (id: string) => void;

  // Approval Queue
  addApprovalRequest: (request: ApprovalRequest) => void;
  removeApprovalRequest: (id: string) => void;
  getApprovalByTicketId: (ticketId: string) => ApprovalRequest | undefined;
}

export const useTicketStore = create<TicketState>((set, get) => {
  // Load initial data from localStorage
  const savedTickets = loadFromLocalStorage<Ticket[]>('TICKETS');
  const initialTickets = savedTickets
    ? savedTickets.map((t) => ({
        ...t,
        createdAt: new Date(t.createdAt),
        updatedAt: new Date(t.updatedAt),
      }))
    : [];

  const savedApprovals = loadFromLocalStorage<ApprovalRequest[]>('APPROVALS');
  const initialApprovals = savedApprovals
    ? savedApprovals.map((a) => ({
        ...a,
        createdAt: new Date(a.createdAt),
      }))
    : [];

  return {
    // Initial State
    tickets: initialTickets,
    approvalQueue: initialApprovals,

    // Actions
    setTickets: (tickets) => {
      saveToLocalStorage('TICKETS', tickets);
      set({ tickets });
    },

    addTicket: (ticket) =>
      set((state) => {
        // Prevent duplicates
        if (state.tickets.find((t) => t.id === ticket.id)) {
          return state;
        }
        const updated = [...state.tickets, ticket];
        saveToLocalStorage('TICKETS', updated);
        return { tickets: updated };
      }),

    updateTicket: (id, updates) =>
      set((state) => {
        const updated = state.tickets.map((ticket) =>
          ticket.id === id ? { ...ticket, ...updates, updatedAt: new Date() } : ticket
        );
        saveToLocalStorage('TICKETS', updated);
        return { tickets: updated };
      }),

    deleteTicket: (id) =>
      set((state) => {
        const updated = state.tickets.filter((ticket) => ticket.id !== id);
        saveToLocalStorage('TICKETS', updated);
        return { tickets: updated };
      }),

    // Approval Queue
    addApprovalRequest: (request) =>
      set((state) => {
        // Prevent duplicates
        if (state.approvalQueue.find((r) => r.id === request.id)) {
          return state;
        }
        const updated = [...state.approvalQueue, request];
        saveToLocalStorage('APPROVALS', updated);
        return { approvalQueue: updated };
      }),

    removeApprovalRequest: (id) =>
      set((state) => {
        const updated = state.approvalQueue.filter((r) => r.id !== id && r.ticketId !== id);
        saveToLocalStorage('APPROVALS', updated);
        return { approvalQueue: updated };
      }),

    getApprovalByTicketId: (ticketId) =>
      get().approvalQueue.find((r) => r.ticketId === ticketId),
  };
});
