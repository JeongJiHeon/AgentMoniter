"""
Workflow State Manager - Redis-backed workflow state management
Replaces in-memory WorkflowManager with persistent Redis storage
"""
import asyncio
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# Import from orchestration (will be updated to use new AgentResult)
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.agent_result import AgentLifecycleStatus, AgentResult
from services.redis_service import redis_service


class StepStatus(str, Enum):
    """Workflow step status (legacy compatibility)"""
    PENDING = "pending"
    RUNNING = "running"
    WAITING_USER = "waiting_user"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowStep:
    """Enhanced workflow step with lifecycle status"""

    def __init__(
        self,
        id: str,
        agent_id: str,
        agent_name: str,
        description: str,
        order: int,
        lifecycle_status: AgentLifecycleStatus = AgentLifecycleStatus.IDLE,
        pending_question: Optional[str] = None,
        required_inputs: Optional[List[str]] = None,
        last_result: Optional[AgentResult] = None,
        # Legacy fields
        needs_user_input: bool = False,
        input_prompt: str = "",
        status: StepStatus = StepStatus.PENDING,
        user_input: Optional[str] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None
    ):
        self.id = id
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.description = description
        self.order = order

        # New lifecycle fields
        self.lifecycle_status = lifecycle_status
        self.pending_question = pending_question
        self.required_inputs = required_inputs
        self.last_result = last_result

        # Legacy fields (for backward compatibility)
        self.needs_user_input = needs_user_input
        self.input_prompt = input_prompt
        self.status = status
        self.user_input = user_input
        self.started_at = started_at
        self.completed_at = completed_at

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for Redis storage"""
        result = {
            "id": self.id,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "description": self.description,
            "order": self.order,
            "lifecycle_status": self.lifecycle_status.value,
            "pending_question": self.pending_question,
            "required_inputs": self.required_inputs,
            "needs_user_input": self.needs_user_input,
            "input_prompt": self.input_prompt,
            "status": self.status.value,
            "user_input": self.user_input,
        }

        if self.last_result:
            result["last_result"] = self.last_result.to_dict()
        if self.started_at:
            result["started_at"] = self.started_at.isoformat()
        if self.completed_at:
            result["completed_at"] = self.completed_at.isoformat()

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowStep':
        """Deserialize from dict"""
        lifecycle_status = AgentLifecycleStatus(data.get("lifecycle_status", "IDLE"))
        status = StepStatus(data.get("status", "pending"))

        last_result = None
        if "last_result" in data and data["last_result"]:
            last_result = AgentResult.from_dict(data["last_result"])

        started_at = None
        if "started_at" in data and data["started_at"]:
            started_at = datetime.fromisoformat(data["started_at"])

        completed_at = None
        if "completed_at" in data and data["completed_at"]:
            completed_at = datetime.fromisoformat(data["completed_at"])

        return cls(
            id=data["id"],
            agent_id=data["agent_id"],
            agent_name=data["agent_name"],
            description=data["description"],
            order=data["order"],
            lifecycle_status=lifecycle_status,
            pending_question=data.get("pending_question"),
            required_inputs=data.get("required_inputs"),
            last_result=last_result,
            needs_user_input=data.get("needs_user_input", False),
            input_prompt=data.get("input_prompt", ""),
            status=status,
            user_input=data.get("user_input"),
            started_at=started_at,
            completed_at=completed_at
        )


class WorkflowState:
    """Workflow state with Redis persistence"""

    def __init__(
        self,
        task_id: str,
        task_content: str,
        steps: List[WorkflowStep],
        current_step_index: int = 0,
        status: str = "running",
        created_at: Optional[datetime] = None
    ):
        self.task_id = task_id
        self.task_content = task_content
        self.steps = steps
        self.current_step_index = current_step_index
        self.status = status
        self.created_at = created_at or datetime.now()

    def get_current_step(self) -> Optional[WorkflowStep]:
        """Get current step"""
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    def is_completed(self) -> bool:
        """Check if workflow completed"""
        return self.current_step_index >= len(self.steps)

    def advance(self) -> None:
        """Advance to next step"""
        if not self.is_completed():
            self.current_step_index += 1

    def get_results(self) -> List[Dict[str, Any]]:
        """Get results from completed steps"""
        results = []
        for step in self.steps:
            if step.status == StepStatus.COMPLETED and step.last_result:
                results.append({
                    "agent": step.agent_name,
                    "result": step.last_result.message or "",
                    "data": step.last_result.final_data
                })
        return results

    def get_user_inputs(self) -> Dict[str, str]:
        """Get user inputs by step ID"""
        return {
            step.id: step.user_input
            for step in self.steps
            if step.user_input is not None
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for Redis"""
        return {
            "task_id": self.task_id,
            "task_content": self.task_content,
            "steps": [step.to_dict() for step in self.steps],
            "current_step_index": self.current_step_index,
            "status": self.status,
            "created_at": self.created_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowState':
        """Deserialize from dict"""
        steps = [WorkflowStep.from_dict(s) for s in data["steps"]]
        created_at = datetime.fromisoformat(data["created_at"])

        return cls(
            task_id=data["task_id"],
            task_content=data["task_content"],
            steps=steps,
            current_step_index=data["current_step_index"],
            status=data["status"],
            created_at=created_at
        )


class WorkflowStateManager:
    """
    Redis-backed workflow state manager
    Replaces in-memory WorkflowManager
    """

    def __init__(self, redis_client=None):
        """
        Initialize workflow state manager
        Args:
            redis_client: Optional redis service instance
        """
        self.redis_service = redis_client or redis_service
        # Keep in-memory locks for concurrency control
        self._locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    async def _get_lock(self, task_id: str) -> asyncio.Lock:
        """Get or create lock for task_id"""
        async with self._global_lock:
            if task_id not in self._locks:
                self._locks[task_id] = asyncio.Lock()
            return self._locks[task_id]

    async def create_workflow(
        self,
        task_id: str,
        task_content: str,
        steps: List[WorkflowStep]
    ) -> WorkflowState:
        """
        Create new workflow and persist to Redis
        """
        lock = await self._get_lock(task_id)
        async with lock:
            workflow = WorkflowState(
                task_id=task_id,
                task_content=task_content,
                steps=steps,
                current_step_index=0,
                status="running"
            )

            # Persist to Redis
            await self._persist_workflow(workflow)

            return workflow

    async def get_workflow(self, task_id: str) -> Optional[WorkflowState]:
        """Load workflow from Redis"""
        lock = await self._get_lock(task_id)
        async with lock:
            state_dict = await self.redis_service.get_workflow_state(task_id)
            if not state_dict:
                return None

            # Deserialize WorkflowState
            return WorkflowState.from_dict(state_dict)

    async def update_step_status(
        self,
        task_id: str,
        step_index: int,
        lifecycle_status: AgentLifecycleStatus,
        result: Optional[AgentResult] = None
    ):
        """
        Update step status and persist
        """
        lock = await self._get_lock(task_id)
        async with lock:
            workflow = await self.get_workflow(task_id)
            if not workflow or step_index >= len(workflow.steps):
                return

            step = workflow.steps[step_index]
            step.lifecycle_status = lifecycle_status

            if result:
                step.last_result = result
                step.pending_question = result.message if lifecycle_status == AgentLifecycleStatus.WAITING_USER else None
                step.required_inputs = result.required_inputs if lifecycle_status == AgentLifecycleStatus.WAITING_USER else None

            # Update legacy status for backward compatibility
            if lifecycle_status == AgentLifecycleStatus.RUNNING:
                step.status = StepStatus.RUNNING
                if not step.started_at:
                    step.started_at = datetime.now()
            elif lifecycle_status == AgentLifecycleStatus.COMPLETED:
                step.status = StepStatus.COMPLETED
                step.completed_at = datetime.now()
            elif lifecycle_status == AgentLifecycleStatus.FAILED:
                step.status = StepStatus.FAILED
                step.completed_at = datetime.now()
            elif lifecycle_status == AgentLifecycleStatus.WAITING_USER:
                step.status = StepStatus.WAITING_USER

            await self._persist_workflow(workflow)

    async def add_user_input(self, task_id: str, user_input: str):
        """
        Add user input to current step
        CRITICAL: Do NOT auto-advance or change status
        """
        lock = await self._get_lock(task_id)
        async with lock:
            workflow = await self.get_workflow(task_id)
            if not workflow:
                return

            current_step = workflow.get_current_step()
            if current_step:
                current_step.user_input = user_input

            # Do NOT change status or advance
            # Let agent.run() decide based on AgentResult

            await self._persist_workflow(workflow)

    async def set_workflow_status(self, task_id: str, status: str):
        """Set workflow status"""
        lock = await self._get_lock(task_id)
        async with lock:
            workflow = await self.get_workflow(task_id)
            if workflow:
                workflow.status = status
                await self._persist_workflow(workflow)

    async def advance_workflow(self, task_id: str):
        """
        Advance to next step
        Only called when step status is COMPLETED
        """
        lock = await self._get_lock(task_id)
        async with lock:
            workflow = await self.get_workflow(task_id)
            if workflow and not workflow.is_completed():
                workflow.advance()
                await self._persist_workflow(workflow)

    async def remove_workflow(self, task_id: str):
        """Remove workflow from Redis"""
        lock = await self._get_lock(task_id)
        async with lock:
            await self.redis_service.delete_workflow_state(task_id)
            # Clean up lock
            async with self._global_lock:
                self._locks.pop(task_id, None)

    async def list_active_workflows(self) -> List[str]:
        """Get list of all active workflow task IDs"""
        return await self.redis_service.list_active_workflows()

    async def _persist_workflow(self, workflow: WorkflowState):
        """Serialize and save workflow to Redis"""
        await self.redis_service.save_workflow_state(
            workflow.task_id,
            workflow.to_dict()
        )

    async def add_workflow_result(self, task_id: str, result: Dict[str, Any]):
        """Add step result to workflow results list"""
        await self.redis_service.add_workflow_result(task_id, result)

    async def get_workflow_results(self, task_id: str) -> List[Dict[str, Any]]:
        """Get all step results for workflow"""
        return await self.redis_service.get_workflow_results(task_id)


# Global singleton instance
workflow_state_manager = WorkflowStateManager()
