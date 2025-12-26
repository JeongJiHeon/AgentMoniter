"""
Agent Result Types - Agent Lifecycle Contract
Agents declare their status, Orchestrator reacts accordingly
"""
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, List


class AgentLifecycleStatus(str, Enum):
    """
    Agent lifecycle status - explicitly declared by agent
    Orchestrator uses this to make state transition decisions
    """
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    WAITING_USER = "WAITING_USER"  # Agent needs user input
    COMPLETED = "COMPLETED"  # Agent finished successfully
    FAILED = "FAILED"  # Agent encountered an error


@dataclass
class InputSchema:
    """
    Schema for required user inputs
    Used by UI to render appropriate input widgets
    """
    type: str  # 'text' | 'select' | 'multi-select'
    placeholder: Optional[str] = None
    choices: Optional[List[Dict[str, str]]] = None  # [{"id": "...", "label": "..."}]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization"""
        result = {"type": self.type}
        if self.placeholder:
            result["placeholder"] = self.placeholder
        if self.choices:
            result["choices"] = self.choices
        return result


@dataclass
class AgentResult:
    """
    Agent execution result - the contract between Agent and Orchestrator

    Agent declares its status, Orchestrator reacts:
    - WAITING_USER: Pause workflow, wait for user input
    - RUNNING: Continue processing (for async operations)
    - COMPLETED: Advance to next step
    - FAILED: Stop workflow with error

    This prevents the orchestrator from "deciding" what to do -
    the agent explicitly declares its state.
    """
    status: AgentLifecycleStatus
    message: Optional[str] = None  # Human-readable message or question
    required_inputs: Optional[List[str]] = None  # List of input field names needed
    input_schema: Optional[InputSchema] = None  # Schema for UI rendering
    partial_data: Optional[Dict[str, Any]] = None  # Intermediate results
    final_data: Optional[Dict[str, Any]] = None  # Final results when status=COMPLETED
    error: Optional[Dict[str, Any]] = None  # Error details when status=FAILED

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization"""
        result = {
            "status": self.status.value,
        }
        if self.message:
            result["message"] = self.message
        if self.required_inputs:
            result["requiredInputs"] = self.required_inputs
        if self.input_schema:
            result["inputSchema"] = self.input_schema.to_dict()
        if self.partial_data:
            result["partialData"] = self.partial_data
        if self.final_data:
            result["finalData"] = self.final_data
        if self.error:
            result["error"] = self.error
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentResult':
        """Create AgentResult from dict"""
        input_schema = None
        if "inputSchema" in data or "input_schema" in data:
            schema_data = data.get("inputSchema") or data.get("input_schema")
            if schema_data:
                input_schema = InputSchema(
                    type=schema_data["type"],
                    placeholder=schema_data.get("placeholder"),
                    choices=schema_data.get("choices")
                )

        return cls(
            status=AgentLifecycleStatus(data["status"]),
            message=data.get("message"),
            required_inputs=data.get("requiredInputs") or data.get("required_inputs"),
            input_schema=input_schema,
            partial_data=data.get("partialData") or data.get("partial_data"),
            final_data=data.get("finalData") or data.get("final_data"),
            error=data.get("error")
        )

    def is_waiting_user(self) -> bool:
        """Check if agent is waiting for user input"""
        return self.status == AgentLifecycleStatus.WAITING_USER

    def is_completed(self) -> bool:
        """Check if agent completed successfully"""
        return self.status == AgentLifecycleStatus.COMPLETED

    def is_failed(self) -> bool:
        """Check if agent failed"""
        return self.status == AgentLifecycleStatus.FAILED

    def is_running(self) -> bool:
        """Check if agent is still running"""
        return self.status == AgentLifecycleStatus.RUNNING


# Helper functions for creating AgentResults

def waiting_user(message: str, input_schema: Optional[InputSchema] = None,
                 required_inputs: Optional[List[str]] = None,
                 partial_data: Optional[Dict[str, Any]] = None) -> AgentResult:
    """Create WAITING_USER result"""
    return AgentResult(
        status=AgentLifecycleStatus.WAITING_USER,
        message=message,
        input_schema=input_schema,
        required_inputs=required_inputs,
        partial_data=partial_data
    )


def completed(final_data: Dict[str, Any], message: Optional[str] = None) -> AgentResult:
    """Create COMPLETED result"""
    return AgentResult(
        status=AgentLifecycleStatus.COMPLETED,
        message=message,
        final_data=final_data
    )


def failed(error_message: str, error_code: Optional[str] = None,
           raw_error: Optional[Any] = None) -> AgentResult:
    """Create FAILED result"""
    error = {"message": error_message}
    if error_code:
        error["code"] = error_code
    if raw_error:
        error["raw"] = str(raw_error)

    return AgentResult(
        status=AgentLifecycleStatus.FAILED,
        error=error,
        message=error_message
    )


def running(message: Optional[str] = None, partial_data: Optional[Dict[str, Any]] = None) -> AgentResult:
    """Create RUNNING result"""
    return AgentResult(
        status=AgentLifecycleStatus.RUNNING,
        message=message,
        partial_data=partial_data
    )
