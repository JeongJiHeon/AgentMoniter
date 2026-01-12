"""
Tool Executor for the tool system.
Handles tool execution with validation, timeout, retries, and error handling.
"""

from typing import Any, Dict, List, Optional, Callable, Awaitable
import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .base_tool import BaseTool, ToolValidationError, ToolExecutionError
from .tool_registry import ToolRegistry, get_tool_registry
from .tool_schemas import ToolResult, ToolCall, ToolCallResult

logger = logging.getLogger(__name__)


class ExecutionStatus(str, Enum):
    """Status of tool execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    APPROVAL_REQUIRED = "approval_required"


@dataclass
class ExecutionContext:
    """Context for tool execution."""
    session_id: str
    agent_id: Optional[str] = None
    user_id: Optional[str] = None
    task_id: Optional[str] = None
    parent_call_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionRecord:
    """Record of a tool execution."""
    call_id: str
    tool_name: str
    arguments: Dict[str, Any]
    status: ExecutionStatus
    result: Optional[ToolResult] = None
    context: Optional[ExecutionContext] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "call_id": self.call_id,
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "status": self.status.value,
            "result": self.result.to_dict() if self.result else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
        }


# Type for approval callback
ApprovalCallback = Callable[[str, str, Dict[str, Any]], Awaitable[bool]]


class ToolExecutor:
    """
    Executes tools with proper validation, timeout, and error handling.

    Features:
    - Parameter validation
    - Timeout handling
    - Retry logic
    - Execution history
    - Approval workflow for dangerous tools
    - Parallel execution support

    Example:
        executor = ToolExecutor()

        # Execute a single tool
        result = await executor.execute(
            "read_file",
            {"file_path": "/path/to/file"}
        )

        # Execute multiple tools in parallel
        results = await executor.execute_parallel([
            ToolCall(id="1", tool_name="read_file", arguments={"file_path": "a.txt"}),
            ToolCall(id="2", tool_name="read_file", arguments={"file_path": "b.txt"}),
        ])
    """

    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        default_timeout: int = 30,
        max_parallel: int = 10,
        approval_callback: Optional[ApprovalCallback] = None,
    ):
        """
        Initialize the executor.

        Args:
            registry: Tool registry to use (defaults to global registry)
            default_timeout: Default timeout in seconds
            max_parallel: Maximum parallel executions
            approval_callback: Callback for approval requests
        """
        self.registry = registry or get_tool_registry()
        self.default_timeout = default_timeout
        self.max_parallel = max_parallel
        self.approval_callback = approval_callback

        # Execution history
        self._history: List[ExecutionRecord] = []
        self._max_history = 1000

        # Active executions
        self._active: Dict[str, ExecutionRecord] = {}

        # Semaphore for parallel execution limit
        self._semaphore = asyncio.Semaphore(max_parallel)

    async def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: Optional[ExecutionContext] = None,
        timeout: Optional[int] = None,
        retry_count: int = 0,
        skip_approval: bool = False,
    ) -> ToolResult:
        """
        Execute a tool by name.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            context: Execution context
            timeout: Override default timeout
            retry_count: Number of retries on failure
            skip_approval: Skip approval for dangerous tools

        Returns:
            ToolResult with execution result
        """
        call_id = str(uuid.uuid4())

        # Create execution record
        record = ExecutionRecord(
            call_id=call_id,
            tool_name=tool_name,
            arguments=arguments,
            status=ExecutionStatus.PENDING,
            context=context,
        )
        self._active[call_id] = record

        try:
            # Get the tool
            tool = self.registry.get(tool_name)
            if not tool:
                record.status = ExecutionStatus.FAILED
                record.error_message = f"Tool '{tool_name}' not found or disabled"
                return ToolResult.error_result(
                    record.error_message,
                    "ToolNotFoundError"
                )

            # Check if approval is required
            if tool.requires_approval and not skip_approval:
                if not self.approval_callback:
                    record.status = ExecutionStatus.APPROVAL_REQUIRED
                    record.error_message = "Approval required but no callback set"
                    return ToolResult.error_result(
                        f"Tool '{tool_name}' requires approval",
                        "ApprovalRequiredError"
                    )

                # Request approval
                approved = await self.approval_callback(
                    tool_name,
                    tool.description,
                    arguments
                )

                if not approved:
                    record.status = ExecutionStatus.CANCELLED
                    record.error_message = "Execution denied by approval"
                    return ToolResult.error_result(
                        "Tool execution denied",
                        "ApprovalDeniedError"
                    )

            # Execute with semaphore
            async with self._semaphore:
                record.status = ExecutionStatus.RUNNING
                record.started_at = datetime.utcnow()

                # Determine timeout
                execution_timeout = timeout or tool.timeout_seconds or self.default_timeout

                # Execute with retries
                last_error = None
                max_retries = retry_count if retry_count > 0 else tool.max_retries

                for attempt in range(max_retries + 1):
                    try:
                        result = await tool.validate_and_execute(**arguments)

                        if result.success:
                            record.status = ExecutionStatus.COMPLETED
                            record.result = result
                            record.completed_at = datetime.utcnow()
                            return result
                        else:
                            last_error = result.error
                            if attempt < max_retries:
                                logger.warning(
                                    f"Tool {tool_name} failed (attempt {attempt + 1}): {last_error}"
                                )
                                await asyncio.sleep(0.5 * (attempt + 1))  # Backoff
                            continue

                    except asyncio.TimeoutError:
                        last_error = f"Timeout after {execution_timeout}s"
                        record.status = ExecutionStatus.TIMEOUT
                        if attempt < max_retries:
                            logger.warning(f"Tool {tool_name} timeout (attempt {attempt + 1})")
                            continue
                        break

                    except Exception as e:
                        last_error = str(e)
                        if attempt < max_retries:
                            logger.warning(f"Tool {tool_name} error (attempt {attempt + 1}): {e}")
                            await asyncio.sleep(0.5 * (attempt + 1))
                            continue
                        break

                # All retries failed
                record.status = ExecutionStatus.FAILED
                record.error_message = last_error
                record.completed_at = datetime.utcnow()
                return ToolResult.error_result(
                    last_error or "Unknown error",
                    "ExecutionError"
                )

        finally:
            # Move to history
            del self._active[call_id]
            self._add_to_history(record)

    async def execute_call(
        self,
        call: ToolCall,
        context: Optional[ExecutionContext] = None,
        **kwargs,
    ) -> ToolCallResult:
        """
        Execute a ToolCall object.

        Args:
            call: The tool call to execute
            context: Execution context
            **kwargs: Additional arguments for execute()

        Returns:
            ToolCallResult with call and result
        """
        result = await self.execute(
            call.tool_name,
            call.arguments,
            context=context,
            **kwargs,
        )

        return ToolCallResult(call=call, result=result)

    async def execute_parallel(
        self,
        calls: List[ToolCall],
        context: Optional[ExecutionContext] = None,
        stop_on_error: bool = False,
        **kwargs,
    ) -> List[ToolCallResult]:
        """
        Execute multiple tool calls in parallel.

        Args:
            calls: List of tool calls to execute
            context: Shared execution context
            stop_on_error: Stop all executions if one fails
            **kwargs: Additional arguments for execute()

        Returns:
            List of ToolCallResults
        """
        if stop_on_error:
            # Use asyncio.gather with return_exceptions=False
            async def execute_with_cancel(call: ToolCall):
                return await self.execute_call(call, context, **kwargs)

            tasks = [execute_with_cancel(call) for call in calls]

            try:
                results = await asyncio.gather(*tasks)
                return list(results)
            except Exception:
                # Cancel remaining tasks
                for task in tasks:
                    if isinstance(task, asyncio.Task) and not task.done():
                        task.cancel()
                raise
        else:
            # Execute all, collect results including errors
            async def execute_safe(call: ToolCall) -> ToolCallResult:
                try:
                    return await self.execute_call(call, context, **kwargs)
                except Exception as e:
                    return ToolCallResult(
                        call=call,
                        result=ToolResult.error_result(str(e), type(e).__name__)
                    )

            tasks = [execute_safe(call) for call in calls]
            results = await asyncio.gather(*tasks)
            return list(results)

    async def execute_sequential(
        self,
        calls: List[ToolCall],
        context: Optional[ExecutionContext] = None,
        stop_on_error: bool = True,
        **kwargs,
    ) -> List[ToolCallResult]:
        """
        Execute tool calls sequentially.

        Args:
            calls: List of tool calls to execute
            context: Shared execution context
            stop_on_error: Stop execution if one fails
            **kwargs: Additional arguments for execute()

        Returns:
            List of ToolCallResults
        """
        results = []

        for call in calls:
            result = await self.execute_call(call, context, **kwargs)
            results.append(result)

            if stop_on_error and not result.result.success:
                break

        return results

    def _add_to_history(self, record: ExecutionRecord) -> None:
        """Add execution record to history."""
        self._history.append(record)

        # Trim history if too long
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

    def get_history(
        self,
        tool_name: Optional[str] = None,
        status: Optional[ExecutionStatus] = None,
        limit: int = 100,
    ) -> List[ExecutionRecord]:
        """
        Get execution history.

        Args:
            tool_name: Filter by tool name
            status: Filter by status
            limit: Maximum records to return

        Returns:
            List of execution records
        """
        records = self._history

        if tool_name:
            records = [r for r in records if r.tool_name == tool_name]

        if status:
            records = [r for r in records if r.status == status]

        return records[-limit:]

    def get_active_executions(self) -> List[ExecutionRecord]:
        """Get currently active executions."""
        return list(self._active.values())

    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        total = len(self._history)
        if total == 0:
            return {
                "total_executions": 0,
                "success_rate": 0,
                "average_duration_ms": 0,
                "by_status": {},
                "by_tool": {},
            }

        # Count by status
        by_status = {}
        for record in self._history:
            status = record.status.value
            by_status[status] = by_status.get(status, 0) + 1

        # Count by tool
        by_tool = {}
        for record in self._history:
            tool = record.tool_name
            by_tool[tool] = by_tool.get(tool, 0) + 1

        # Calculate success rate
        completed = by_status.get("completed", 0)
        success_rate = (completed / total) * 100 if total > 0 else 0

        # Calculate average duration
        durations = []
        for record in self._history:
            if record.started_at and record.completed_at:
                duration = (record.completed_at - record.started_at).total_seconds() * 1000
                durations.append(duration)

        avg_duration = sum(durations) / len(durations) if durations else 0

        return {
            "total_executions": total,
            "success_rate": round(success_rate, 2),
            "average_duration_ms": round(avg_duration, 2),
            "active_executions": len(self._active),
            "by_status": by_status,
            "by_tool": by_tool,
        }

    def clear_history(self) -> None:
        """Clear execution history."""
        self._history.clear()

    def set_approval_callback(self, callback: ApprovalCallback) -> None:
        """Set the approval callback."""
        self.approval_callback = callback
