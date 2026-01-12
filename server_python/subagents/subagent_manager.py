"""
Sub-agent Manager for hierarchical agent systems.
Allows parent agents to spawn child agents for specialized tasks.
"""

import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class SubagentStatus(str, Enum):
    """Status of a sub-agent."""
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class SubagentSpec:
    """Specification for a sub-agent."""
    name: str
    role: str
    task: str
    capabilities: List[str] = field(default_factory=list)
    allowed_tools: Optional[List[str]] = None
    max_iterations: int = 10
    timeout_seconds: Optional[int] = None
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "role": self.role,
            "task": self.task,
            "capabilities": self.capabilities,
            "allowed_tools": self.allowed_tools,
            "max_iterations": self.max_iterations,
            "timeout_seconds": self.timeout_seconds,
            "context": self.context,
        }


@dataclass
class SubagentResult:
    """Result from a sub-agent execution."""
    success: bool
    output: Any = None
    error: Optional[str] = None
    iterations: int = 0
    execution_time_ms: float = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "iterations": self.iterations,
            "execution_time_ms": self.execution_time_ms,
            "metadata": self.metadata,
        }


@dataclass
class SubagentInstance:
    """A running sub-agent instance."""
    id: str
    spec: SubagentSpec
    status: SubagentStatus
    parent_id: Optional[str] = None
    result: Optional[SubagentResult] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    children: List[str] = field(default_factory=list)  # Child sub-agent IDs

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "spec": self.spec.to_dict(),
            "status": self.status.value,
            "parent_id": self.parent_id,
            "result": self.result.to_dict() if self.result else None,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "children": self.children,
        }


# Type for agent execution function
AgentExecuteFunc = Callable[[SubagentSpec], Awaitable[SubagentResult]]


class SubagentManager:
    """
    Manages sub-agent spawning and coordination.

    Features:
    - Spawn specialized child agents
    - Hierarchical agent trees
    - Result aggregation
    - Resource management

    Example:
        manager = SubagentManager(execute_agent=my_agent_executor)

        # Spawn a sub-agent
        spec = SubagentSpec(
            name="FileSearcher",
            role="Search for files matching criteria",
            task="Find all Python files in /project",
            capabilities=["file_search", "glob"],
        )

        result = await manager.spawn_and_wait(spec, parent_id="main_agent")

        # Spawn multiple sub-agents in parallel
        results = await manager.spawn_parallel([spec1, spec2, spec3])
    """

    def __init__(
        self,
        execute_agent: AgentExecuteFunc,
        max_depth: int = 3,
        max_concurrent: int = 5,
    ):
        """
        Initialize the sub-agent manager.

        Args:
            execute_agent: Function to execute an agent
            max_depth: Maximum sub-agent nesting depth
            max_concurrent: Maximum concurrent sub-agents
        """
        self.execute_agent = execute_agent
        self.max_depth = max_depth
        self.max_concurrent = max_concurrent

        self._instances: Dict[str, SubagentInstance] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def spawn(
        self,
        spec: SubagentSpec,
        parent_id: Optional[str] = None,
    ) -> str:
        """
        Spawn a new sub-agent.

        Args:
            spec: Sub-agent specification
            parent_id: ID of parent agent

        Returns:
            Sub-agent ID
        """
        # Check depth limit
        if parent_id:
            depth = self._get_depth(parent_id)
            if depth >= self.max_depth:
                raise ValueError(f"Maximum nesting depth ({self.max_depth}) exceeded")

        # Create instance
        instance_id = str(uuid.uuid4())
        instance = SubagentInstance(
            id=instance_id,
            spec=spec,
            status=SubagentStatus.INITIALIZING,
            parent_id=parent_id,
        )

        self._instances[instance_id] = instance

        # Register with parent
        if parent_id and parent_id in self._instances:
            self._instances[parent_id].children.append(instance_id)

        logger.info(
            f"Spawned sub-agent '{spec.name}' (id={instance_id}, parent={parent_id})"
        )

        # Start execution
        asyncio.create_task(self._execute_subagent(instance_id))

        return instance_id

    async def spawn_and_wait(
        self,
        spec: SubagentSpec,
        parent_id: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> SubagentResult:
        """
        Spawn a sub-agent and wait for completion.

        Args:
            spec: Sub-agent specification
            parent_id: ID of parent agent
            timeout: Timeout in seconds

        Returns:
            SubagentResult
        """
        instance_id = await self.spawn(spec, parent_id)

        # Wait for completion
        try:
            result = await asyncio.wait_for(
                self._wait_for_completion(instance_id),
                timeout=timeout or spec.timeout_seconds,
            )
            return result

        except asyncio.TimeoutError:
            # Cancel the sub-agent
            await self.cancel(instance_id)

            return SubagentResult(
                success=False,
                error=f"Sub-agent timed out after {timeout}s",
            )

    async def spawn_parallel(
        self,
        specs: List[SubagentSpec],
        parent_id: Optional[str] = None,
        stop_on_error: bool = False,
    ) -> List[SubagentResult]:
        """
        Spawn multiple sub-agents in parallel.

        Args:
            specs: List of sub-agent specifications
            parent_id: ID of parent agent
            stop_on_error: Stop all if one fails

        Returns:
            List of SubagentResults
        """
        logger.info(f"Spawning {len(specs)} sub-agents in parallel")

        # Spawn all
        instance_ids = []
        for spec in specs:
            instance_id = await self.spawn(spec, parent_id)
            instance_ids.append(instance_id)

        # Wait for all
        tasks = [
            self._wait_for_completion(instance_id)
            for instance_id in instance_ids
        ]

        if stop_on_error:
            results = await asyncio.gather(*tasks)
        else:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Convert exceptions to failed results
            final_results = []
            for result in results:
                if isinstance(result, Exception):
                    final_results.append(SubagentResult(
                        success=False,
                        error=str(result),
                    ))
                else:
                    final_results.append(result)
            results = final_results

        return results

    async def spawn_sequential(
        self,
        specs: List[SubagentSpec],
        parent_id: Optional[str] = None,
        stop_on_error: bool = True,
    ) -> List[SubagentResult]:
        """
        Spawn sub-agents sequentially.

        Args:
            specs: List of sub-agent specifications
            parent_id: ID of parent agent
            stop_on_error: Stop if one fails

        Returns:
            List of SubagentResults
        """
        logger.info(f"Spawning {len(specs)} sub-agents sequentially")

        results = []

        for spec in specs:
            result = await self.spawn_and_wait(spec, parent_id)
            results.append(result)

            if stop_on_error and not result.success:
                break

        return results

    async def cancel(self, instance_id: str) -> bool:
        """
        Cancel a running sub-agent.

        Args:
            instance_id: Sub-agent ID

        Returns:
            True if cancelled
        """
        instance = self._instances.get(instance_id)
        if not instance:
            return False

        if instance.status in (SubagentStatus.COMPLETED, SubagentStatus.FAILED):
            return False

        instance.status = SubagentStatus.CANCELLED
        instance.completed_at = datetime.utcnow()

        logger.info(f"Cancelled sub-agent {instance_id}")

        return True

    def get_instance(self, instance_id: str) -> Optional[SubagentInstance]:
        """Get a sub-agent instance by ID."""
        return self._instances.get(instance_id)

    def get_children(self, parent_id: str) -> List[SubagentInstance]:
        """Get all child sub-agents of a parent."""
        parent = self._instances.get(parent_id)
        if not parent:
            return []

        return [
            self._instances[child_id]
            for child_id in parent.children
            if child_id in self._instances
        ]

    def get_tree(self, root_id: str) -> Dict[str, Any]:
        """
        Get the full sub-agent tree starting from root.

        Args:
            root_id: Root agent ID

        Returns:
            Tree structure as nested dict
        """
        instance = self._instances.get(root_id)
        if not instance:
            return {}

        tree = instance.to_dict()
        tree["children"] = [
            self.get_tree(child_id)
            for child_id in instance.children
        ]

        return tree

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about sub-agents."""
        status_counts = {}
        for status in SubagentStatus:
            status_counts[status.value] = sum(
                1 for inst in self._instances.values()
                if inst.status == status
            )

        return {
            "total_subagents": len(self._instances),
            "status_counts": status_counts,
            "max_depth": self.max_depth,
            "max_concurrent": self.max_concurrent,
        }

    async def _execute_subagent(self, instance_id: str) -> None:
        """Execute a sub-agent."""
        instance = self._instances.get(instance_id)
        if not instance:
            return

        async with self._semaphore:
            instance.status = SubagentStatus.RUNNING
            instance.started_at = datetime.utcnow()

            try:
                # Execute the agent
                result = await self.execute_agent(instance.spec)

                instance.result = result
                instance.status = (
                    SubagentStatus.COMPLETED if result.success
                    else SubagentStatus.FAILED
                )

            except Exception as e:
                logger.exception(f"Sub-agent execution failed: {instance_id}")

                instance.result = SubagentResult(
                    success=False,
                    error=str(e),
                )
                instance.status = SubagentStatus.FAILED

            finally:
                instance.completed_at = datetime.utcnow()

    async def _wait_for_completion(self, instance_id: str) -> SubagentResult:
        """Wait for a sub-agent to complete."""
        while True:
            instance = self._instances.get(instance_id)
            if not instance:
                return SubagentResult(
                    success=False,
                    error="Sub-agent not found",
                )

            if instance.status in (
                SubagentStatus.COMPLETED,
                SubagentStatus.FAILED,
                SubagentStatus.CANCELLED,
            ):
                return instance.result or SubagentResult(
                    success=False,
                    error="No result available",
                )

            await asyncio.sleep(0.1)

    def _get_depth(self, instance_id: str) -> int:
        """Get the nesting depth of an instance."""
        instance = self._instances.get(instance_id)
        if not instance or not instance.parent_id:
            return 0

        return 1 + self._get_depth(instance.parent_id)

    def clear(self) -> None:
        """Clear all sub-agent instances."""
        self._instances.clear()
