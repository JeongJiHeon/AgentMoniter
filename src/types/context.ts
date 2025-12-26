// App outlet context type
export interface AppOutletContext {
  handleApprove: (ticketId: string) => void;
  handleReject: (ticketId: string) => void;
  handleSelectOption: (ticketId: string, optionId: string) => void;
  handleApprovalRespond: (requestId: string, response: string) => void;
  handleCreateAgent: (config: any) => void;
  handleAssignAgent: (taskId: string, agentId: string) => void;
  handleRespondInteraction: (interactionId: string, response: string) => void;
  handleSendTaskMessage: (taskId: string, message: string) => void;
}
