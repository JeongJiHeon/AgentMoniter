"""
Graph Executor for executing task graphs.
Handles parallel execution, dependency management, and error recovery.
"""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Callable, Awaitable
from dataclasses import dataclass

from .dag import TaskGraph, TaskNode, TaskStatus, ExecutionResult

logger = logging.getLogger(__name__)


# Type for task execution function
TaskExecuteFunc = Callable[[TaskNode], Awaitable[ExecutionResult]]


@dataclass
class ExecutionConfig:
    """Configuration for graph execution."""
    max_parallel: int = 5
    stop_on_error: bool = False
    retry_failed: bool = False
    max_retries: int = 3
    timeout_seconds: Optional[int] = None


class GraphExecutor:
    """
    Executes a task graph respecting dependencies and parallelism.

    Features:
    - Parallel execution of independent tasks
    - Dependency resolution
    - Error handling and retry logic
    - Progress tracking

    Example:
        executor = GraphExecutor(graph, execute_task_func=my_executor)

        result = await executor.execute_all(
            config=ExecutionConfig(max_parallel=3, stop_on_error=True)
        )
    """

    def __init__(
        self,
        graph: TaskGraph,
        execute_task: TaskExecuteFunc,
        config: Optional[ExecutionConfig] = None,
    ):
        """
        Initialize the graph executor.

        Args:
            graph: The task graph to execute
            execute_task: Async function to execute a single task
            config: Execution configuration
        """
        self.graph = graph
        self.execute_task = execute_task
        self.config = config or ExecutionConfig()

        self._semaphore = asyncio.Semaphore(self.config.max_parallel)
        self._active_tasks: Dict[str, asyncio.Task] = {}
        self._start_time: Optional[float] = None

    async def execute_all(self) -> Dict[str, Any]:
        """
        Execute all tasks in the graph.

        Returns:
            Dict with execution results and statistics
        """
        self._start_time = time.time()

        logger.info(f"Starting execution of graph '{self.graph.name}'")
        logger.info(f"Total tasks: {len(self.graph.get_all_nodes())}")

        try:
            # Get execution batches
            batches = self.graph.get_parallel_batches()

            logger.info(f"Execution will run in {len(batches)} batch(es)")

            # Execute each batch
            for batch_num, batch in enumerate(batches, 1):
                logger.info(
                    f"Executing batch {batch_num}/{len(batches)} "
                    f"({len(batch)} task(s))"
                )

                results = await self._execute_batch(batch)

                # Check for errors
                failed = [r for r in results if not r.success]
                if failed and self.config.stop_on_error:
                    logger.error(f"Stopping execution due to {len(failed)} failed task(s)")
                    break

            # Generate final report
            elapsed = time.time() - self._start_time
            stats = self.graph.get_stats()

            completed = stats["status_counts"].get("completed", 0)
            failed = stats["status_counts"].get("failed", 0)
            total = stats["total_tasks"]

            success_rate = (completed / total * 100) if total > 0 else 0

            result = {
                "success": failed == 0,
                "total_tasks": total,
                "completed": completed,
                "failed": failed,
                "success_rate": round(success_rate, 2),
                "execution_time_seconds": round(elapsed, 2),
                "batches_executed": len(batches),
                "stats": stats,
                "graph_name": self.graph.name,
            }

            logger.info(
                f"Execution complete: {completed}/{total} successful "
                f"({success_rate:.1f}%) in {elapsed:.2f}s"
            )

            return result

        except Exception as e:
            logger.exception(f"Error during graph execution: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "stats": self.graph.get_stats(),
            }

    async def execute_node(self, node_id: str) -> ExecutionResult:
        """
        Execute a single node.

        Args:
            node_id: ID of the node to execute

        Returns:
            ExecutionResult
        """
        node = self.graph.get_node(node_id)
        if not node:
            return ExecutionResult(
                success=False,
                error=f"Node not found: {node_id}",
            )

        return await self._execute_single_task(node)

    async def _execute_batch(
        self,
        batch: List[TaskNode],
    ) -> List[ExecutionResult]:
        """Execute a batch of tasks in parallel."""
        tasks = []

        for node in batch:
            task = asyncio.create_task(self._execute_single_task(node))
            tasks.append(task)
            self._active_tasks[node.id] = task

        # Wait for all tasks in batch
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Clean up active tasks
        for node in batch:
            self._active_tasks.pop(node.id, None)

        # Convert exceptions to failed results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(ExecutionResult(
                    success=False,
                    error=str(result),
                ))
            else:
                final_results.append(result)

        return final_results

    async def _execute_single_task(
        self,
        node: TaskNode,
    ) -> ExecutionResult:
        """Execute a single task with retry logic."""
        async with self._semaphore:
            # Update status
            self.graph.update_task_status(node.id, TaskStatus.RUNNING)

            logger.debug(f"Executing task: {node.name}")

            start_time = time.time()
            last_error = None

            # Retry loop
            max_attempts = self.config.max_retries + 1 if self.config.retry_failed else 1

            for attempt in range(max_attempts):
                try:
                    # Execute with timeout if configured
                    if self.config.timeout_seconds:
                        result = await asyncio.wait_for(
                            self.execute_task(node),
                            timeout=self.config.timeout_seconds
                        )
                    else:
                        result = await self.execute_task(node)

                    # Add execution time
                    result.execution_time_ms = (time.time() - start_time) * 1000

                    # Update graph
                    if result.success:
                        self.graph.update_task_status(
                            node.id,
                            TaskStatus.COMPLETED,
                            result
                        )
                        logger.debug(
                            f"Task completed: {node.name} "
                            f"({result.execution_time_ms:.0f}ms)"
                        )
                        return result
                    else:
                        last_error = result.error
                        if attempt < max_attempts - 1:
                            logger.warning(
                                f"Task failed (attempt {attempt + 1}/{max_attempts}): "
                                f"{node.name} - {result.error}"
                            )
                            await asyncio.sleep(0.5 * (attempt + 1))  # Backoff
                            continue
                        else:
                            break

                except asyncio.TimeoutError:
                    last_error = f"Timeout after {self.config.timeout_seconds}s"
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Task timeout (attempt {attempt + 1}/{max_attempts}): "
                            f"{node.name}"
                        )
                        continue
                    else:
                        break

                except Exception as e:
                    last_error = str(e)
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Task error (attempt {attempt + 1}/{max_attempts}): "
                            f"{node.name} - {e}"
                        )
                        await asyncio.sleep(0.5 * (attempt + 1))
                        continue
                    else:
                        logger.exception(f"Task failed: {node.name}")
                        break

            # All attempts failed
            result = ExecutionResult(
                success=False,
                error=last_error or "Unknown error",
                execution_time_ms=(time.time() - start_time) * 1000,
            )

            self.graph.update_task_status(
                node.id,
                TaskStatus.FAILED,
                result
            )

            return result

    def get_progress(self) -> Dict[str, Any]:
        """Get current execution progress."""
        stats = self.graph.get_stats()
        total = stats["total_tasks"]

        if total == 0:
            return {
                "progress_percent": 0,
                "completed": 0,
                "total": 0,
                "active": 0,
            }

        completed = stats["status_counts"].get("completed", 0)
        failed = stats["status_counts"].get("failed", 0)
        done = completed + failed

        progress = (done / total * 100) if total > 0 else 0

        return {
            "progress_percent": round(progress, 2),
            "completed": completed,
            "failed": failed,
            "active": len(self._active_tasks),
            "total": total,
            "elapsed_seconds": round(time.time() - self._start_time, 2) if self._start_time else 0,
        }

    def cancel_all(self) -> None:
        """Cancel all active tasks."""
        logger.warning("Cancelling all active tasks")

        for task_id, task in self._active_tasks.items():
            task.cancel()
            node = self.graph.get_node(task_id)
            if node:
                self.graph.update_task_status(task_id, TaskStatus.CANCELLED)

        self._active_tasks.clear()
