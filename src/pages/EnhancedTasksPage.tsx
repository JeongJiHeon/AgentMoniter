import { useState, useMemo } from 'react';
import { useOutletContext } from 'react-router-dom';
import { useTaskStore } from '../stores';
import { useAllAgents } from '../hooks/useAllAgents';
import { EnhancedTaskList } from '../components/enhanced/EnhancedTaskList';
import { TaskGraphPanel } from '../components/enhanced/TaskGraphPanel';
import { AgentInsightsPanel } from '../components/enhanced/AgentInsightsPanel';
import { CommandBar } from '../components/enhanced/CommandBar';
import { CreateTaskModal } from '../components/tasks/CreateTaskModal';

interface OutletContext {
  handleApprove: (ticketId: string) => void;
  handleReject: (ticketId: string, reason?: string) => void;
  handleSelectOption: (ticketId: string, optionId: string) => void;
  handleApprovalRespond: (requestId: string, approved: boolean, comment?: string) => void;
  handleCreateAgent: (name: string, description: string, type: string, capabilities: string[]) => void;
  handleAssignAgent: (taskId: string, agentId: string) => void;
  handleRespondInteraction: (interactionId: string, response: string) => void;
  handleSendTaskMessage: (taskId: string, message: string) => void;
  showCreateTaskModal: boolean;
  setShowCreateTaskModal: (show: boolean) => void;
  showCreateAgentModal: boolean;
  setShowCreateAgentModal: (show: boolean) => void;
}

export function EnhancedTasksPage() {
  const allAgents = useAllAgents();
  const {
    tasks,
    autoAssignMode,
    setAutoAssignMode,
    agentLogs,
    updateTask,
    deleteTask,
  } = useTaskStore();

  const {
    showCreateTaskModal,
    setShowCreateTaskModal,
    handleSendTaskMessage,
  } = useOutletContext<OutletContext>();

  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [insightsPanelOpen, setInsightsPanelOpen] = useState(true);

  // Selected task
  const selectedTask = useMemo(() =>
    tasks.find(t => t.id === selectedTaskId),
    [tasks, selectedTaskId]
  );

  // Task statistics
  const stats = useMemo(() => ({
    total: tasks.length,
    pending: tasks.filter(t => t.status === 'pending').length,
    inProgress: tasks.filter(t => t.status === 'in_progress').length,
    completed: tasks.filter(t => t.status === 'completed').length,
    failed: tasks.filter(t => t.status === 'failed').length,
  }), [tasks]);

  return (
    <div className="h-screen bg-[#0a0e1a] text-gray-100 overflow-hidden font-mono">
      {/* Background grid effect */}
      <div className="fixed inset-0 bg-[linear-gradient(rgba(34,211,238,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(34,211,238,0.03)_1px,transparent_1px)] bg-[size:40px_40px] pointer-events-none" />

      {/* Scanline effect */}
      <div className="fixed inset-0 bg-[linear-gradient(transparent_50%,rgba(0,217,255,0.02)_50%)] bg-[size:100%_4px] pointer-events-none animate-scanline" />

      <div className="relative z-10 h-full flex flex-col">
        {/* Command Bar */}
        <CommandBar
          stats={stats}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          onCreateTask={() => setShowCreateTaskModal(true)}
          autoAssignMode={autoAssignMode}
          onAutoAssignModeChange={setAutoAssignMode}
        />

        {/* Main Content Grid */}
        <div className="flex-1 grid grid-cols-12 gap-3 p-3 overflow-hidden">
          {/* Left Panel - Task List */}
          <div className="col-span-3 flex flex-col overflow-hidden">
            <EnhancedTaskList
              tasks={tasks}
              selectedTaskId={selectedTaskId}
              onSelectTask={setSelectedTaskId}
              searchQuery={searchQuery}
              agents={allAgents}
              onUpdateTask={updateTask}
              onDeleteTask={deleteTask}
            />
          </div>

          {/* Center Panel - Task Graph Visualization */}
          <div className={`${insightsPanelOpen ? 'col-span-6' : 'col-span-9'} flex flex-col overflow-hidden transition-all duration-300`}>
            <TaskGraphPanel
              task={selectedTask}
              allTasks={tasks}
              agents={allAgents}
              onSendMessage={handleSendTaskMessage}
            />
          </div>

          {/* Right Panel - Agent Insights (Collapsible) */}
          {insightsPanelOpen && (
            <div className="col-span-3 flex flex-col overflow-hidden">
              <AgentInsightsPanel
                task={selectedTask}
                agents={allAgents}
                agentLogs={agentLogs}
                onClose={() => setInsightsPanelOpen(false)}
              />
            </div>
          )}

          {/* Toggle insights panel button */}
          {!insightsPanelOpen && (
            <button
              onClick={() => setInsightsPanelOpen(true)}
              className="fixed right-3 top-24 bg-gradient-to-br from-cyan-500/20 to-magenta-500/20 border border-cyan-400/30 rounded-lg p-2 backdrop-blur-xl hover:border-cyan-400/50 transition-all group"
              aria-label="Open insights panel"
            >
              <svg className="w-5 h-5 text-cyan-400 group-hover:text-cyan-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Create Task Modal */}
      {showCreateTaskModal && (
        <CreateTaskModal
          isOpen={showCreateTaskModal}
          onClose={() => setShowCreateTaskModal(false)}
          onCreateTask={(task) => {
            // This will be handled by the parent component
            console.log('Create task:', task);
          }}
        />
      )}

      {/* Custom styles */}
      <style>{`
        @keyframes scanline {
          0% { transform: translateY(0); }
          100% { transform: translateY(100vh); }
        }
        .animate-scanline {
          animation: scanline 8s linear infinite;
        }

        /* Custom scrollbar */
        ::-webkit-scrollbar {
          width: 6px;
          height: 6px;
        }
        ::-webkit-scrollbar-track {
          background: rgba(17, 24, 39, 0.3);
        }
        ::-webkit-scrollbar-thumb {
          background: rgba(34, 211, 238, 0.3);
          border-radius: 3px;
        }
        ::-webkit-scrollbar-thumb:hover {
          background: rgba(34, 211, 238, 0.5);
        }
      `}</style>
    </div>
  );
}
