from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
from uuid import UUID
from models.agent import Agent, AgentStateUpdate, ThinkingMode
from models.ticket import Ticket, CreateTicketInput
from models.approval import ApprovalRequest
from models.ontology import OntologyContext


class AgentEventType:
    STATE_CHANGED = "state_changed"
    TICKET_CREATED = "ticket_created"
    TICKET_UPDATED = "ticket_updated"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_RECEIVED = "approval_received"
    ERROR = "error"
    WARNING = "warning"
    LOG = "log"


class AgentEvent:
    def __init__(
        self,
        type: str,
        agent_id: str,
        timestamp: datetime,
        payload: Any
    ):
        self.type = type
        self.agent_id = agent_id
        self.timestamp = timestamp
        self.payload = payload


AgentEventHandler = Callable[[AgentEvent], None]


class AgentExecutionContext:
    def __init__(
        self,
        agent_id: str,
        ontology_context: OntologyContext,
        current_ticket: Optional[Ticket] = None,
        previous_decisions: Optional[List[Dict[str, Any]]] = None
    ):
        self.agent_id = agent_id
        self.ontology_context = ontology_context
        self.current_ticket = current_ticket
        self.previous_decisions = previous_decisions or []


class AgentInput:
    def __init__(
        self,
        type: str,  # 'email' | 'document' | 'message' | 'task' | 'event'
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        source: Optional[Dict[str, str]] = None
    ):
        self.type = type
        self.content = content
        self.metadata = metadata or {}
        self.source = source


class AgentOutput:
    def __init__(
        self,
        type: str = 'result',
        result: Optional[Dict[str, Any]] = None,
        tickets: Optional[List[CreateTicketInput]] = None,
        approval_requests: Optional[List[Dict[str, Any]]] = None,
        logs: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.type = type
        self.result = result or {}
        self.tickets = tickets or []
        self.approval_requests = approval_requests or []
        self.logs = logs or []
        self.metadata = metadata or {}


class AgentConfig:
    def __init__(
        self,
        name: str,
        type: str,
        description: Optional[str] = None,
        permissions: Optional[Dict[str, Any]] = None,
        constraints: Optional[List[Dict[str, str]]] = None,
        capabilities: Optional[List[str]] = None,
        custom_config: Optional[Dict[str, Any]] = None
    ):
        self.name = name
        self.type = type
        self.description = description
        self.permissions = permissions or {}
        self.constraints = constraints or []
        self.capabilities = capabilities or ['general']
        self.custom_config = custom_config or {}


class IAgent(ABC):
    @property
    @abstractmethod
    def id(self) -> str:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def type(self) -> str:
        pass

    @abstractmethod
    def get_state(self) -> Agent:
        pass

    @abstractmethod
    def get_thinking_mode(self) -> ThinkingMode:
        pass

    @abstractmethod
    def is_active(self) -> bool:
        pass

    @abstractmethod
    async def initialize(self, context: AgentExecutionContext) -> None:
        pass

    @abstractmethod
    async def start(self) -> None:
        pass

    @abstractmethod
    async def pause(self) -> None:
        pass

    @abstractmethod
    async def resume(self) -> None:
        pass

    @abstractmethod
    async def stop(self) -> None:
        pass

    @abstractmethod
    async def process(self, input: AgentInput) -> AgentOutput:
        pass

    @abstractmethod
    async def on_approval_received(self, approval: ApprovalRequest) -> None:
        pass

    @abstractmethod
    async def update_state(self, update: AgentStateUpdate) -> None:
        pass

    @abstractmethod
    def on(self, event_type: str, handler: AgentEventHandler) -> None:
        pass

    @abstractmethod
    def off(self, event_type: str, handler: AgentEventHandler) -> None:
        pass

    @abstractmethod
    def emit(self, event: AgentEvent) -> None:
        pass


class IAgentFactory(ABC):
    @abstractmethod
    def create(self, config: AgentConfig) -> IAgent:
        pass

    @abstractmethod
    def get_available_types(self) -> List[str]:
        pass

