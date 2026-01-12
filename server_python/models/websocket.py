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
    TASK_INTERACTION = "task_interaction"
    CHAT_MESSAGE_RESPONSE = "chat_message_response"
    TASK_GRAPH_UPDATE = "task_graph_update"
    AGENT_MEMORY_UPDATE = "agent_memory_update"

    # Client -> Server
    ASSIGN_TASK = "assign_task"
    TASK_INTERACTION_CLIENT = "task_interaction"
    CHAT_MESSAGE = "chat_message"
    CREATE_AGENT = "create_agent"
    APPROVE_REQUEST = "approve_request"
    REJECT_REQUEST = "reject_request"
    SELECT_OPTION = "select_option"
    PROVIDE_INPUT = "provide_input"
    CANCEL_TICKET = "cancel_ticket"
    PAUSE_AGENT = "pause_agent"
    RESUME_AGENT = "resume_agent"
    UPDATE_LLM_CONFIG = "update_llm_config"  # LLM 설정 동기화
    REQUEST_TASK_GRAPH = "request_task_graph"
    REQUEST_AGENT_MEMORY = "request_agent_memory"

