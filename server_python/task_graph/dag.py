"""
Directed Acyclic Graph (DAG) for task management.
Represents tasks and their dependencies as a graph structure.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Status of a task node."""
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


@dataclass
class ExecutionResult:
    """Result of task execution."""
    success: bool
    output: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "metadata": self.metadata,
        }


@dataclass
class TaskNode:
    """
    A node in the task graph.

    Represents a single task with dependencies and execution state.
    """
    id: str
    name: str
    description: str
    dependencies: Set[str] = field(default_factory=set)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[ExecutionResult] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Task-specific data
    task_type: str = "generic"  # e.g., "tool_call", "llm_generation", "subtask"
    task_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "dependencies": list(self.dependencies),
            "status": self.status.value,
            "result": self.result.to_dict() if self.result else None,
            "metadata": self.metadata,
            "task_type": self.task_type,
            "task_data": self.task_data,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    def is_ready(self, graph: "TaskGraph") -> bool:
        """Check if task is ready to execute (all dependencies completed)."""
        if self.status != TaskStatus.PENDING:
            return False

        for dep_id in self.dependencies:
            dep_node = graph.get_node(dep_id)
            if not dep_node or dep_node.status != TaskStatus.COMPLETED:
                return False

        return True

    def can_run_parallel_with(self, other: "TaskNode") -> bool:
        """Check if this task can run in parallel with another."""
        # Cannot run in parallel if there's a dependency relationship
        if self.id in other.dependencies or other.id in self.dependencies:
            return False

        # Cannot run in parallel if they share dependencies (potential resource conflict)
        # This is a conservative check - could be relaxed based on task types
        return len(self.dependencies & other.dependencies) == 0


class TaskGraph:
    """
    Directed Acyclic Graph for task management.

    Manages tasks and their dependencies, ensuring proper execution order.

    Example:
        graph = TaskGraph()

        # Add tasks
        task1 = graph.add_task("Read file", "Read config.json")
        task2 = graph.add_task("Parse config", "Parse JSON", dependencies={task1})
        task3 = graph.add_task("Validate config", "Check required fields", dependencies={task2})

        # Execute
        executor = GraphExecutor(graph)
        results = await executor.execute_all()
    """

    def __init__(self, name: Optional[str] = None):
        """Initialize the task graph."""
        self.name = name or f"graph_{uuid.uuid4().hex[:8]}"
        self._nodes: Dict[str, TaskNode] = {}
        self._execution_order: List[str] = []

    def add_task(
        self,
        name: str,
        description: str,
        dependencies: Optional[Set[str]] = None,
        task_type: str = "generic",
        task_data: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None,
        **metadata,
    ) -> str:
        """
        Add a task to the graph.

        Args:
            name: Task name
            description: Task description
            dependencies: Set of task IDs this task depends on
            task_type: Type of task
            task_data: Task-specific data
            task_id: Optional custom task ID
            **metadata: Additional metadata

        Returns:
            Task ID

        Raises:
            ValueError: If dependencies create a cycle
        """
        task_id = task_id or f"task_{uuid.uuid4().hex[:8]}"
        dependencies = dependencies or set()

        # Validate dependencies exist
        for dep_id in dependencies:
            if dep_id not in self._nodes:
                raise ValueError(f"Dependency task not found: {dep_id}")

        # Check for cycles
        if self._would_create_cycle(task_id, dependencies):
            raise ValueError("Adding this task would create a cycle in the graph")

        # Create node
        node = TaskNode(
            id=task_id,
            name=name,
            description=description,
            dependencies=dependencies,
            task_type=task_type,
            task_data=task_data or {},
            metadata=metadata,
        )

        self._nodes[task_id] = node
        logger.debug(f"Added task {task_id}: {name}")

        return task_id

    def add_dependency(self, task_id: str, depends_on: str) -> None:
        """
        Add a dependency between tasks.

        Args:
            task_id: The task that depends on another
            depends_on: The task to depend on

        Raises:
            ValueError: If either task doesn't exist or cycle would be created
        """
        if task_id not in self._nodes:
            raise ValueError(f"Task not found: {task_id}")
        if depends_on not in self._nodes:
            raise ValueError(f"Dependency task not found: {depends_on}")

        new_deps = self._nodes[task_id].dependencies | {depends_on}

        if self._would_create_cycle(task_id, new_deps):
            raise ValueError("Adding this dependency would create a cycle")

        self._nodes[task_id].dependencies.add(depends_on)

    def remove_task(self, task_id: str) -> None:
        """Remove a task from the graph."""
        if task_id not in self._nodes:
            return

        # Remove dependencies on this task from other tasks
        for node in self._nodes.values():
            node.dependencies.discard(task_id)

        del self._nodes[task_id]
        logger.debug(f"Removed task {task_id}")

    def get_node(self, task_id: str) -> Optional[TaskNode]:
        """Get a task node by ID."""
        return self._nodes.get(task_id)

    def get_all_nodes(self) -> List[TaskNode]:
        """Get all task nodes."""
        return list(self._nodes.values())

    def get_ready_tasks(self) -> List[TaskNode]:
        """Get all tasks that are ready to execute."""
        ready = []
        for node in self._nodes.values():
            if node.is_ready(self):
                ready.append(node)
        return ready

    def get_parallel_batches(self) -> List[List[TaskNode]]:
        """
        Get tasks grouped into batches that can run in parallel.

        Returns:
            List of batches, where each batch contains tasks that can run in parallel
        """
        batches = []
        remaining = set(self._nodes.keys())

        while remaining:
            # Find all tasks ready to run
            ready = []
            for task_id in remaining:
                node = self._nodes[task_id]
                if all(dep_id not in remaining for dep_id in node.dependencies):
                    ready.append(node)

            if not ready:
                # This shouldn't happen if graph is acyclic
                logger.error("No ready tasks found but tasks remain - possible cycle!")
                break

            batches.append(ready)
            for node in ready:
                remaining.remove(node.id)

        return batches

    def get_topological_order(self) -> List[str]:
        """
        Get tasks in topological order (dependencies first).

        Returns:
            List of task IDs in execution order

        Raises:
            ValueError: If graph contains a cycle
        """
        # Kahn's algorithm
        in_degree = {task_id: 0 for task_id in self._nodes}
        for node in self._nodes.values():
            for dep_id in node.dependencies:
                in_degree[dep_id] += 1

        queue = [task_id for task_id, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            task_id = queue.pop(0)
            result.append(task_id)

            # Reduce in-degree for dependent tasks
            for node in self._nodes.values():
                if task_id in node.dependencies:
                    in_degree[node.id] -= 1
                    if in_degree[node.id] == 0:
                        queue.append(node.id)

        if len(result) != len(self._nodes):
            raise ValueError("Graph contains a cycle")

        return result

    def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        result: Optional[ExecutionResult] = None,
    ) -> None:
        """Update the status of a task."""
        node = self._nodes.get(task_id)
        if not node:
            return

        node.status = status

        if status == TaskStatus.RUNNING and not node.started_at:
            node.started_at = datetime.utcnow()

        if status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.SKIPPED):
            node.completed_at = datetime.utcnow()
            if result:
                node.result = result

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the graph."""
        status_counts = {}
        for status in TaskStatus:
            status_counts[status.value] = sum(
                1 for node in self._nodes.values()
                if node.status == status
            )

        return {
            "total_tasks": len(self._nodes),
            "status_counts": status_counts,
            "graph_name": self.name,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert graph to dictionary."""
        return {
            "name": self.name,
            "nodes": {
                task_id: node.to_dict()
                for task_id, node in self._nodes.items()
            },
            "stats": self.get_stats(),
        }

    def visualize_dot(self) -> str:
        """
        Generate DOT format for visualization with Graphviz.

        Returns:
            DOT format string
        """
        lines = ["digraph TaskGraph {"]
        lines.append("  rankdir=TB;")
        lines.append("  node [shape=box];")

        # Add nodes
        for node in self._nodes.values():
            color = {
                TaskStatus.PENDING: "lightgray",
                TaskStatus.READY: "yellow",
                TaskStatus.RUNNING: "lightblue",
                TaskStatus.COMPLETED: "lightgreen",
                TaskStatus.FAILED: "red",
                TaskStatus.SKIPPED: "orange",
                TaskStatus.CANCELLED: "gray",
            }.get(node.status, "white")

            label = f"{node.name}\\n({node.status.value})"
            lines.append(f'  "{node.id}" [label="{label}", fillcolor="{color}", style=filled];')

        # Add edges
        for node in self._nodes.values():
            for dep_id in node.dependencies:
                lines.append(f'  "{dep_id}" -> "{node.id}";')

        lines.append("}")
        return "\n".join(lines)

    def _would_create_cycle(self, task_id: str, dependencies: Set[str]) -> bool:
        """Check if adding these dependencies would create a cycle."""
        # DFS to detect cycles
        def has_path(start: str, end: str, visited: Set[str]) -> bool:
            if start == end:
                return True
            if start in visited:
                return False

            visited.add(start)

            # Check dependencies of tasks that depend on start
            for node in self._nodes.values():
                if start in node.dependencies:
                    if has_path(node.id, end, visited):
                        return True

            return False

        # Check if any dependency has a path back to this task
        for dep_id in dependencies:
            if has_path(dep_id, task_id, set()):
                return True

        return False

    def clear(self) -> None:
        """Clear all tasks from the graph."""
        self._nodes.clear()
        self._execution_order.clear()
