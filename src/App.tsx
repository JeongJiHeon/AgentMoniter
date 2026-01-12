import { useCallback, useMemo, useEffect, useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { OrchestrationService } from './services/orchestration';
import { DashboardLayout } from './components/layout/DashboardLayout';
import { ChatPanel } from './components/chat/ChatPanel';
import { ToastContainer } from './components/common/ToastContainer';
import { CommandPalette } from './components/common/CommandPalette';
import { useKeyboardShortcuts } from './hooks/useKeyboardShortcuts';
import {
  useAgentStore,
  useTaskStore,
  useTicketStore,
  useSettingsStore,
  useChatStore,
  useWebSocketStore,
} from './stores';
import { useWebSocket } from './hooks/useWebSocket';
import { useTaskAutoAssignment } from './hooks/useTaskAutoAssignment';
import { useAllAgents } from './hooks/useAllAgents';
import { WEBSOCKET_URL } from './constants';
import type { CustomAgentConfig, PersonalizationItem } from './types';

type TabType = 'dashboard' | 'tasks' | 'personalization' | 'settings';

function App() {
  const location = useLocation();
  const navigate = useNavigate();

  // Command Palette state
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [showCreateTaskModal, setShowCreateTaskModal] = useState(false);
  const [showCreateAgentModal, setShowCreateAgentModal] = useState(false);

  // Derive active tab from URL
  const activeTab: TabType = useMemo(() => {
    const path = location.pathname.slice(1) || 'tasks';
    return path as TabType;
  }, [location.pathname]);

  // Get all agents with proper memoization
  const allAgents = useAllAgents();

  // Store state - use selectors to avoid infinite loops
  const addCustomAgent = useAgentStore((state) => state.addCustomAgent);
  const tasks = useTaskStore((state) => state.tasks);
  const updateTask = useTaskStore((state) => state.updateTask);
  const approvalQueue = useTicketStore((state) => state.approvalQueue);
  const updateTicket = useTicketStore((state) => state.updateTicket);
  const removeApprovalRequest = useTicketStore((state) => state.removeApprovalRequest);
  const getApprovalByTicketId = useTicketStore((state) => state.getApprovalByTicketId);
  const settings = useSettingsStore((state) => state.settings);
  const chatMessages = useChatStore((state) => state.chatMessages);
  const personalizationItems = useChatStore((state) => state.personalizationItems);
  const clearChatMessages = useChatStore((state) => state.clearChatMessages);
  const addPersonalizationItem = useChatStore((state) => state.addPersonalizationItem);
  const sendMessage = useWebSocketStore((state) => state.sendMessage);
  const isConnected = useWebSocketStore((state) => state.isConnected);

  // 🔄 LLM 설정 동기화: WebSocket 연결 후 & 설정 변경 시 백엔드에 전송
  useEffect(() => {
    if (isConnected && settings.llmConfig) {
      console.log('[App] Syncing LLM config to backend:', settings.llmConfig);
      sendMessage({
        type: 'update_llm_config',
        payload: {
          provider: settings.llmConfig.provider,
          model: settings.llmConfig.model,
          apiKey: settings.llmConfig.apiKey,
          baseUrl: settings.llmConfig.baseUrl,
          temperature: settings.llmConfig.temperature,
          maxTokens: settings.llmConfig.maxTokens,
        },
        timestamp: new Date().toISOString(),
      });
    }
  }, [isConnected, settings.llmConfig, sendMessage]);

  // OrchestrationService (business logic) - useMemo로 즉시 초기화
  const orchestrationService = useMemo(
    () => new OrchestrationService(settings.llmConfig),
    [settings.llmConfig]
  );

  // Initialize WebSocket connection
  useWebSocket({ url: WEBSOCKET_URL });

  // Auto-assignment hook
  useTaskAutoAssignment(orchestrationService);

  // ===== Handlers =====

  // Ticket & Approval handlers
  const handleApprove = useCallback(
    (ticketId: string) => {
      console.log(`[App] handleApprove called for ticket ${ticketId}`);

      const approvalRequest = getApprovalByTicketId(ticketId);

      // Update ticket status locally
      updateTicket(ticketId, { status: 'approved' });

      // Remove from approval queue
      removeApprovalRequest(ticketId);

      if (!approvalRequest) {
        console.warn(`[App] Approval request not found for ticket ${ticketId}`);
        return;
      }

      // Send approval message to backend
      sendMessage({
        type: 'approve_request',
        payload: {
          requestId: approvalRequest.id,
          ticketId,
          agentId: approvalRequest.agentId,
          decision: 'approve',
        },
        timestamp: new Date().toISOString(),
      });

      console.log(`[App] Sent approve_request for ticket ${ticketId}`);
    },
    [getApprovalByTicketId, updateTicket, removeApprovalRequest, sendMessage]
  );

  const handleReject = useCallback(
    (ticketId: string) => {
      console.log(`[App] handleReject called for ticket ${ticketId}`);

      const approvalRequest = getApprovalByTicketId(ticketId);

      // Update ticket status locally
      updateTicket(ticketId, { status: 'rejected' });

      // Remove from approval queue
      removeApprovalRequest(ticketId);

      if (!approvalRequest) {
        console.warn(`[App] Approval request not found for ticket ${ticketId}`);
        return;
      }

      // Send rejection message to backend
      sendMessage({
        type: 'reject_request',
        payload: {
          requestId: approvalRequest.id,
          ticketId,
          agentId: approvalRequest.agentId,
          decision: 'reject',
        },
        timestamp: new Date().toISOString(),
      });

      console.log(`[App] Sent reject_request for ticket ${ticketId}`);
    },
    [getApprovalByTicketId, updateTicket, removeApprovalRequest, sendMessage]
  );

  const handleSelectOption = useCallback(
    (ticketId: string, optionId: string) => {
      console.log(`[App] handleSelectOption: ticketId=${ticketId}, optionId=${optionId}`);

      const approvalRequest = getApprovalByTicketId(ticketId);

      // Update ticket status locally
      updateTicket(ticketId, { status: 'approved' });

      // Remove from approval queue
      removeApprovalRequest(ticketId);

      if (!approvalRequest) {
        console.warn(`[App] Approval request not found for ticket ${ticketId}`);
        return;
      }

      // Send option selection to backend
      sendMessage({
        type: 'select_option',
        payload: {
          requestId: approvalRequest.id,
          ticketId,
          agentId: approvalRequest.agentId,
          optionId,
        },
        timestamp: new Date().toISOString(),
      });

      console.log(`[App] Sent select_option for ticket ${ticketId}`);
    },
    [getApprovalByTicketId, updateTicket, removeApprovalRequest, sendMessage]
  );

  const handleApprovalRespond = useCallback(
    (requestId: string, response: string) => {
      console.log(`[App] handleApprovalRespond: requestId=${requestId}, response=${response}`);

      const request = approvalQueue.find((r) => r.id === requestId);
      if (!request) {
        console.warn(`[App] Approval request not found: ${requestId}`);
        return;
      }

      if (response === 'approve') {
        handleApprove(request.ticketId);
      } else if (response === 'reject') {
        handleReject(request.ticketId);
      } else {
        handleSelectOption(request.ticketId, response);
      }
    },
    [approvalQueue, handleApprove, handleReject, handleSelectOption]
  );

  // Personalization handlers
  const handleAddPersonalizationItem = useCallback(
    (item: Omit<PersonalizationItem, 'id' | 'createdAt' | 'updatedAt'>) => {
      const newItem: PersonalizationItem = {
        ...item,
        id: crypto.randomUUID(),
        createdAt: new Date(),
        updatedAt: new Date(),
      };
      addPersonalizationItem(newItem);
    },
    [addPersonalizationItem]
  );

  const handleSaveInsightFromChat = useCallback(
    (content: string) => {
      handleAddPersonalizationItem({
        content,
        category: 'insight',
        source: 'chat',
      });
    },
    [handleAddPersonalizationItem]
  );

  const handleAutoSavePersonalization = useCallback(
    (items: Omit<PersonalizationItem, 'id' | 'createdAt' | 'updatedAt' | 'source'>[]) => {
      items.forEach((item) => {
        handleAddPersonalizationItem({
          ...item,
          source: 'chat',
        });
      });
    },
    [handleAddPersonalizationItem]
  );

  // Custom agent handlers
  const handleCreateAgent = useCallback(
    (config: Omit<CustomAgentConfig, 'id' | 'createdAt' | 'updatedAt'>) => {
      const newAgent: CustomAgentConfig = {
        ...config,
        id: crypto.randomUUID(),
        createdAt: new Date(),
        updatedAt: new Date(),
      };

      // Add to store
      addCustomAgent(newAgent);

      // Send to backend
      sendMessage({
        type: 'create_agent',
        payload: {
          id: newAgent.id,
          name: newAgent.name,
          type: newAgent.type,
          description: newAgent.description,
          systemPrompt: newAgent.systemPrompt,
          constraints: newAgent.constraints || [],
          allowedMCPs: newAgent.allowedMCPs || [],
        },
        timestamp: new Date().toISOString(),
      });

      console.log(`[App] Created agent: ${newAgent.name}`);
    },
    [addCustomAgent, sendMessage]
  );

  // Task handlers
  const handleAssignAgent = useCallback(
    (taskId: string, agentId: string) => {
      const task = tasks.find((t) => t.id === taskId);
      if (!task) {
        console.error(`[App] Task ${taskId} not found`);
        return;
      }

      // Update task locally
      updateTask(taskId, { assignedAgentId: agentId, status: 'in_progress' });

      // Send assignment to backend
      sendMessage({
        type: 'assign_task',
        payload: {
          taskId,
          agentId,
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

      console.log(`[App] Assigned task ${taskId} to agent ${agentId}`);
    },
    [tasks, updateTask, sendMessage]
  );

  const handleRespondInteraction = useCallback(
    (interactionId: string, response: string) => {
      // Send response to backend
      sendMessage({
        type: 'respond_interaction',
        payload: {
          interactionId,
          response,
        },
        timestamp: new Date().toISOString(),
      });

      console.log(`[App] Responded to interaction ${interactionId}`);
    },
    [sendMessage]
  );

  const handleSendTaskMessage = useCallback(
    (taskId: string, message: string) => {
      // Send task interaction to backend
      sendMessage({
        type: 'task_interaction',
        payload: {
          taskId,
          role: 'user',
          message,
        },
        timestamp: new Date().toISOString(),
      });

      console.log(`[App] Sent task message for task ${taskId}`);
    },
    [sendMessage]
  );

  const handleSendChatMessage = useCallback(
    (message: string) => {
      console.log(`[App] Sending chat message to Orchestration Agent: ${message}`);

      // Send chat message to backend
      sendMessage({
        type: 'chat_message',
        payload: {
          message,
          timestamp: new Date().toISOString(),
        },
        timestamp: new Date().toISOString(),
      });
    },
    [sendMessage]
  );

  // Tab change handler using navigation
  const handleTabChange = useCallback(
    (tab: TabType) => {
      navigate(`/${tab}`);
    },
    [navigate]
  );

  // Command Palette handlers
  const openCommandPalette = useCallback(() => {
    setIsCommandPaletteOpen(true);
  }, []);

  const closeCommandPalette = useCallback(() => {
    setIsCommandPaletteOpen(false);
  }, []);

  const openCreateTaskModal = useCallback(() => {
    setShowCreateTaskModal(true);
  }, []);

  const openCreateAgentModal = useCallback(() => {
    setShowCreateAgentModal(true);
  }, []);

  // Keyboard shortcuts
  useKeyboardShortcuts({
    shortcuts: [
      {
        key: 'k',
        ctrl: true,
        action: openCommandPalette,
        description: 'Open Command Palette',
      },
      {
        key: 'n',
        ctrl: true,
        action: openCreateTaskModal,
        description: 'Create New Task',
      },
      {
        key: 'a',
        ctrl: true,
        shift: true,
        action: openCreateAgentModal,
        description: 'Create New Agent',
      },
      {
        key: '1',
        action: () => handleTabChange('tasks'),
        description: 'Go to Tasks',
      },
      {
        key: '2',
        action: () => handleTabChange('dashboard'),
        description: 'Go to Dashboard',
      },
      {
        key: '3',
        action: () => handleTabChange('personalization'),
        description: 'Go to Personalization',
      },
      {
        key: '4',
        action: () => handleTabChange('settings'),
        description: 'Go to Settings',
      },
    ],
  });

  return (
    <>
      <ToastContainer />

      {/* Command Palette */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={closeCommandPalette}
        onNavigate={handleTabChange}
        onCreateTask={openCreateTaskModal}
        onCreateAgent={openCreateAgentModal}
      />

      <DashboardLayout
        activeTab={activeTab}
        onTabChange={handleTabChange}
        rightPanel={
          <ChatPanel
            llmConfig={settings.llmConfig}
            agentCount={allAgents.length}
            mcpCount={settings.mcpServices.filter((s) => s.status === 'connected').length}
            personalizationCount={personalizationItems.length}
            onSaveInsight={handleSaveInsightFromChat}
            onAutoSavePersonalization={handleAutoSavePersonalization}
            externalMessages={chatMessages}
            onMessagesRead={clearChatMessages}
            onSendMessage={handleSendChatMessage}
            useOrchestration={true}
          />
        }
      >
        {/* Render routed pages */}
        <Outlet
          context={{
            handleApprove,
            handleReject,
            handleSelectOption,
            handleApprovalRespond,
            handleCreateAgent,
            handleAssignAgent,
            handleRespondInteraction,
            handleSendTaskMessage,
            // Modal controls
            showCreateTaskModal,
            setShowCreateTaskModal,
            showCreateAgentModal,
            setShowCreateAgentModal,
          }}
        />
      </DashboardLayout>
    </>
  );
}

export default App;
