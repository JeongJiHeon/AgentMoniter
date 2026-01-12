import { useOutletContext } from 'react-router-dom';
import { TaskPanel } from '../components/tasks/TaskPanel';
import { useTaskStore, useTicketStore, useSettingsStore } from '../stores';
import { useAllAgents } from '../hooks/useAllAgents';

interface OutletContext {
  handleApprove: (ticketId: string) => void;
  handleReject: (ticketId: string, reason?: string) => void;
  handleSelectOption: (ticketId: string, optionId: string) => void;
  handleApprovalRespond: (requestId: string, approved: boolean, comment?: string) => void;
  handleCreateAgent: (name: string, description: string, type: string, capabilities: string[]) => void;
  handleAssignAgent: (taskId: string, agentId: string) => void;
  handleRespondInteraction: (interactionId: string, response: string) => void;
  handleSendTaskMessage: (taskId: string, message: string) => void;
  // Modal controls
  showCreateTaskModal: boolean;
  setShowCreateTaskModal: (show: boolean) => void;
  showCreateAgentModal: boolean;
  setShowCreateAgentModal: (show: boolean) => void;
}

export function TasksPage() {
  const allAgents = useAllAgents();
  const {
    tasks,
    autoAssignMode,
    setAutoAssignMode,
    interactions,
    taskChatMessages,
    agentLogs,
    updateTask,
    deleteTask,
    clearAllTasks,
    deleteCompletedTasks,
    clearAllLogs
  } = useTaskStore();
  const { tickets, approvalQueue } = useTicketStore();
  const { settings } = useSettingsStore();

  const {
    handleAssignAgent,
    handleRespondInteraction,
    handleSendTaskMessage,
    showCreateTaskModal,
    setShowCreateTaskModal,
  } = useOutletContext<OutletContext>();

  return (
    <div className="max-w-7xl mx-auto">
      <TaskPanel
        tasks={tasks}
        agents={allAgents}
        tickets={tickets}
        approvalRequests={approvalQueue}
        agentLogs={agentLogs}
        interactions={interactions}
        taskChatMessages={taskChatMessages}
        onCreateTask={() => setShowCreateTaskModal(true)}
        onUpdateTask={updateTask}
        onDeleteTask={deleteTask}
        onClearAllTasks={clearAllTasks}
        onDeleteCompletedTasks={deleteCompletedTasks}
        onClearAllLogs={clearAllLogs}
        onAssignAgent={handleAssignAgent}
        onRespondInteraction={handleRespondInteraction}
        onSendTaskMessage={handleSendTaskMessage}
        availableMCPs={settings.mcpServices}
        llmConfig={settings.llmConfig}
        autoAssignMode={autoAssignMode}
        onAutoAssignModeChange={setAutoAssignMode}
        showCreateTaskModal={showCreateTaskModal}
        onCloseCreateTaskModal={() => setShowCreateTaskModal(false)}
      />
    </div>
  );
}
