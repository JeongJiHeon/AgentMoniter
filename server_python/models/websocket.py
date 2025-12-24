from enum import Enum


class WebSocketMessageType(str, Enum):
    # Server -> Client
    AGENT_UPDATE = "agent_update"
    TICKET_CREATED = "ticket_created"
    TICKET_UPDATED = "ticket_updated"
    APPROVAL_REQUEST = "approval_request"
    APPROVAL_RESOLVED = "approval_resolved"
    AGENT_QUESTION = "agent_question"
    SYSTEM_NOTIFICATION = "system_notification"
    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    AGENT_RESPONSE = "agent_response"

    # Client -> Server
    ASSIGN_TASK = "assign_task"
    CREATE_AGENT = "create_agent"
    APPROVE_REQUEST = "approve_request"
    REJECT_REQUEST = "reject_request"
    SELECT_OPTION = "select_option"
    PROVIDE_INPUT = "provide_input"
    CANCEL_TICKET = "cancel_ticket"
    PAUSE_AGENT = "pause_agent"
    RESUME_AGENT = "resume_agent"

