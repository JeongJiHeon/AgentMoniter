import { useEffect, useRef } from 'react';
import { useTaskStore, useWebSocketStore } from '../stores';
import { OrchestrationService } from '../services/orchestration';
import { useAllAgents } from './useAllAgents';

/**
 * Custom hook for automatically assigning tasks to agents
 * based on orchestration rules and auto-assign mode
 */
export function useTaskAutoAssignment(orchestrationService: OrchestrationService | null) {
  const tasks = useTaskStore((state) => state.tasks);
  const autoAssignMode = useTaskStore((state) => state.autoAssignMode);
  const { markTaskAsProcessing, unmarkTaskAsProcessing, isTaskProcessing, updateTask } = useTaskStore();
  const allAgents = useAllAgents();
  const { sendMessage } = useWebSocketStore();

  // Track processing tasks to avoid duplicates
  const processingRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    // Get pending tasks that need assignment
    const pendingTasks = tasks.filter(
      (t) => !t.assignedAgentId && t.status === 'pending'
    );

    if (pendingTasks.length === 0 || !orchestrationService || allAgents.length === 0) {
      return;
    }

    pendingTasks.forEach((task) => {
      // Skip if already being processed
      if (isTaskProcessing(task.id) || processingRef.current.has(task.id)) {
        console.log(`[AutoAssignment] Task ${task.id} is already being processed, skipping...`);
        return;
      }

      // Determine if auto-assignment should happen
      let shouldAutoAssign = false;

      if (autoAssignMode === 'global') {
        // Global auto mode: assign all tasks except explicitly disabled
        shouldAutoAssign = task.autoAssign !== false;
      } else {
        // Manual mode: only assign explicitly enabled tasks or default rules
        if (task.autoAssign === true) {
          shouldAutoAssign = true;
        } else if (task.autoAssign === undefined) {
          // Apply default rules (high priority or from Slack)
          shouldAutoAssign = orchestrationService.shouldAutoAssign(task);
        }
      }

      if (!shouldAutoAssign) {
        return;
      }

      // Check if already assigned (race condition prevention)
      if (task.assignedAgentId) {
        return;
      }

      // Mark as processing
      markTaskAsProcessing(task.id);
      processingRef.current.add(task.id);
      console.log(`[AutoAssignment] Starting to process task ${task.id}...`);

      // Multi-agent planning
      orchestrationService
        .selectAgentsForTask(task, allAgents)
        .then((plan) => {
          if (plan.agents.length > 0) {
            const primaryAgentId = plan.agents[0].agentId;

            // Update task state
            updateTask(task.id, {
              assignedAgentId: primaryAgentId,
              status: 'in_progress',
            });

            // Send assignment message to backend
            sendMessage({
              type: 'assign_task',
              payload: {
                taskId: task.id,
                agentId: primaryAgentId,
                orchestrationPlan: {
                  agents: plan.agents,
                  needsUserInput: plan.needsUserInput,
                  inputPrompt: plan.inputPrompt,
                },
                task: {
                  id: task.id,
                  title: task.title,
                  description: task.description,
                  priority: task.priority,
                  source: task.source,
                  tags: task.tags,
                },
              },
              timestamp: new Date().toISOString(),
            });

            console.log(`[AutoAssignment] Multi-agent plan for task ${task.id}:`, plan.agents.map((a) => a.agentName));
          } else {
            console.warn(`[AutoAssignment] No agents selected for task ${task.id}`);
          }
        })
        .catch((error) => {
          console.error('[AutoAssignment] Error in auto-assignment:', error);
        })
        .finally(() => {
          // Cleanup processing state
          unmarkTaskAsProcessing(task.id);
          processingRef.current.delete(task.id);
          console.log(`[AutoAssignment] Finished processing task ${task.id}`);
        });
    });
  }, [tasks, allAgents, autoAssignMode, orchestrationService, markTaskAsProcessing, unmarkTaskAsProcessing, isTaskProcessing, updateTask, sendMessage]);
}
