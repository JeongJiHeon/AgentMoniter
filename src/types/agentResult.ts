/**
 * Agent Result Types - Agent Lifecycle Contract (Frontend)
 * Matches server_python/agents/agent_result.py
 */

export type AgentLifecycleStatus = 'IDLE' | 'RUNNING' | 'WAITING_USER' | 'COMPLETED' | 'FAILED';

export interface InputSchema {
  type: 'text' | 'select' | 'multi-select';
  placeholder?: string;
  choices?: Array<{ id: string; label: string }>;
}

export interface AgentResult {
  /**
   * Agent lifecycle status - explicitly declared by agent
   * Orchestrator reacts to this status instead of deciding
   */
  status: AgentLifecycleStatus;

  /**
   * Human-readable message or question
   * When status=WAITING_USER, this contains the question
   */
  message?: string;

  /**
   * List of required input field names
   * Used when status=WAITING_USER
   */
  requiredInputs?: string[];

  /**
   * Schema for UI rendering of input widgets
   * Provides structured options for select/multi-select inputs
   */
  inputSchema?: InputSchema;

  /**
   * Intermediate results (for multi-step processing)
   */
  partialData?: Record<string, any>;

  /**
   * Final results when status=COMPLETED
   */
  finalData?: Record<string, any>;

  /**
   * Error details when status=FAILED
   */
  error?: {
    code?: string;
    message: string;
    raw?: any;
  };
}

/**
 * Helper to check if agent is waiting for user input
 */
export function isWaitingUser(result: AgentResult): boolean {
  return result.status === 'WAITING_USER';
}

/**
 * Helper to check if agent completed successfully
 */
export function isCompleted(result: AgentResult): boolean {
  return result.status === 'COMPLETED';
}

/**
 * Helper to check if agent failed
 */
export function isFailed(result: AgentResult): boolean {
  return result.status === 'FAILED';
}

/**
 * Helper to check if agent is still running
 */
export function isRunning(result: AgentResult): boolean {
  return result.status === 'RUNNING';
}

/**
 * Get status badge color for UI
 */
export function getStatusColor(status: AgentLifecycleStatus): string {
  const colors = {
    IDLE: 'gray',
    RUNNING: 'blue',
    WAITING_USER: 'yellow',
    COMPLETED: 'green',
    FAILED: 'red'
  };
  return colors[status];
}

/**
 * Get status label for UI
 */
export function getStatusLabel(status: AgentLifecycleStatus): string {
  const labels = {
    IDLE: 'Idle',
    RUNNING: 'Running',
    WAITING_USER: 'Waiting for Input',
    COMPLETED: 'Completed',
    FAILED: 'Failed'
  };
  return labels[status];
}

/**
 * Get status icon for UI
 */
export function getStatusIcon(status: AgentLifecycleStatus): string {
  const icons = {
    IDLE: '⏸️',
    RUNNING: '🔄',
    WAITING_USER: '❓',
    COMPLETED: '✅',
    FAILED: '❌'
  };
  return icons[status];
}
