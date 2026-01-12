"""
ReAct (Reasoning + Acting) Loop implementation.
Implements the Think → Plan → Act → Observe → Reflect cycle.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from tools.tool_executor import ToolExecutor, ExecutionContext
from tools.tool_schemas import ToolResult, ToolCall

logger = logging.getLogger(__name__)


class StepType(str, Enum):
    """Types of steps in the ReAct loop."""
    THOUGHT = "thought"
    PLAN = "plan"
    ACTION = "action"
    OBSERVATION = "observation"
    REFLECTION = "reflection"
    FINAL_ANSWER = "final_answer"


@dataclass
class ReActStep:
    """A single step in the ReAct loop."""
    step_number: int
    step_type: StepType
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tool_calls: List[ToolCall] = field(default_factory=list)
    tool_results: List[ToolResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "step_number": self.step_number,
            "step_type": self.step_type.value,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "tool_calls": [call.to_dict() for call in self.tool_calls],
            "tool_results": [result.to_dict() for result in self.tool_results],
        }

    def to_context_string(self) -> str:
        """Convert to string for context injection."""
        lines = [f"[{self.step_type.value.upper()} - Step {self.step_number}]"]
        lines.append(self.content)

        if self.tool_calls:
            lines.append("\nActions taken:")
            for call in self.tool_calls:
                lines.append(f"  - {call.tool_name}({call.arguments})")

        if self.tool_results:
            lines.append("\nObservations:")
            for result in self.tool_results:
                if result.success:
                    lines.append(f"  ✓ {result.output}")
                else:
                    lines.append(f"  ✗ Error: {result.error}")

        return "\n".join(lines)


# Type for LLM generation function
LLMGenerateFunc = Callable[[str, List[Dict[str, Any]], Optional[List[Dict]]], Awaitable[Dict[str, Any]]]


class ReActLoop:
    """
    Implements the ReAct (Reasoning + Acting) pattern.

    The loop follows these steps:
    1. THOUGHT: Analyze the current situation and task
    2. PLAN: Decide what actions to take
    3. ACTION: Execute tool calls
    4. OBSERVATION: Collect and analyze results
    5. REFLECTION: Evaluate progress and decide next steps
    6. Repeat or provide FINAL_ANSWER

    Example:
        loop = ReActLoop(
            llm_generate=my_llm_function,
            tool_executor=executor,
            max_iterations=10,
        )

        result = await loop.run(
            task="Find all Python files in the project",
            context={"cwd": "/path/to/project"}
        )
    """

    def __init__(
        self,
        llm_generate: LLMGenerateFunc,
        tool_executor: ToolExecutor,
        max_iterations: int = 15,
        enable_reflection: bool = True,
        enable_self_critique: bool = True,
        stop_on_error: bool = False,
    ):
        """
        Initialize the ReAct loop.

        Args:
            llm_generate: Function to generate LLM responses
            tool_executor: Tool executor for running tools
            max_iterations: Maximum number of loop iterations
            enable_reflection: Enable reflection step
            enable_self_critique: Enable self-critique
            stop_on_error: Stop loop on tool execution error
        """
        self.llm_generate = llm_generate
        self.tool_executor = tool_executor
        self.max_iterations = max_iterations
        self.enable_reflection = enable_reflection
        self.enable_self_critique = enable_self_critique
        self.stop_on_error = stop_on_error

        self._steps: List[ReActStep] = []
        self._current_iteration = 0

    async def run(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        initial_observations: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Run the ReAct loop for a given task.

        Args:
            task: The task to accomplish
            context: Additional context information
            initial_observations: Initial observations to start with

        Returns:
            Dict with final_answer, steps, and metadata
        """
        self._steps = []
        self._current_iteration = 0

        context = context or {}
        initial_observations = initial_observations or []

        logger.info(f"Starting ReAct loop for task: {task[:100]}...")

        try:
            # Build initial context
            conversation_history = []

            # Add initial observations if any
            if initial_observations:
                obs_step = ReActStep(
                    step_number=0,
                    step_type=StepType.OBSERVATION,
                    content="\n".join(initial_observations),
                )
                self._steps.append(obs_step)

            # Main loop
            while self._current_iteration < self.max_iterations:
                self._current_iteration += 1

                logger.debug(f"ReAct iteration {self._current_iteration}/{self.max_iterations}")

                # Step 1: THOUGHT - Analyze current situation
                thought_step = await self._think(task, context, conversation_history)
                self._steps.append(thought_step)

                # Check if we should stop
                if "final_answer" in thought_step.metadata:
                    break

                # Step 2: PLAN - Decide on actions
                plan_step = await self._plan(task, context, conversation_history)
                self._steps.append(plan_step)

                # Step 3: ACTION - Execute tools
                action_step = await self._act(plan_step, context)
                self._steps.append(action_step)

                # Check for errors
                if self.stop_on_error and action_step.metadata.get("has_errors"):
                    logger.warning("Stopping loop due to tool execution errors")
                    break

                # Step 4: OBSERVATION - Collect results
                observation_step = await self._observe(action_step)
                self._steps.append(observation_step)

                # Step 5: REFLECTION - Evaluate progress
                if self.enable_reflection:
                    reflection_step = await self._reflect(task, context, conversation_history)
                    self._steps.append(reflection_step)

                    # Check if task is complete
                    if reflection_step.metadata.get("task_complete"):
                        # Get final answer
                        final_step = await self._generate_final_answer(task, conversation_history)
                        self._steps.append(final_step)
                        break

                # Update conversation history
                conversation_history = self._build_conversation_history()

            # Generate final answer if not already done
            if not self._steps or self._steps[-1].step_type != StepType.FINAL_ANSWER:
                final_step = await self._generate_final_answer(task, conversation_history)
                self._steps.append(final_step)

            # Build result
            result = {
                "success": True,
                "final_answer": self._steps[-1].content,
                "steps": [step.to_dict() for step in self._steps],
                "total_iterations": self._current_iteration,
                "total_steps": len(self._steps),
                "metadata": {
                    "task": task,
                    "context": context,
                    "completed_normally": self._current_iteration < self.max_iterations,
                }
            }

            logger.info(f"ReAct loop completed in {self._current_iteration} iterations")
            return result

        except Exception as e:
            logger.exception(f"Error in ReAct loop: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "steps": [step.to_dict() for step in self._steps],
                "total_iterations": self._current_iteration,
            }

    async def _think(
        self,
        task: str,
        context: Dict[str, Any],
        history: List[Dict[str, Any]],
    ) -> ReActStep:
        """Generate a thought about the current situation."""
        prompt = self._build_thought_prompt(task, context, history)

        response = await self.llm_generate(
            prompt,
            history,
            None,  # No tools for thinking
        )

        content = response.get("content", "")

        return ReActStep(
            step_number=len(self._steps) + 1,
            step_type=StepType.THOUGHT,
            content=content,
            metadata={"prompt": prompt},
        )

    async def _plan(
        self,
        task: str,
        context: Dict[str, Any],
        history: List[Dict[str, Any]],
    ) -> ReActStep:
        """Generate a plan for what to do next."""
        prompt = self._build_plan_prompt(task, context, history)

        response = await self.llm_generate(
            prompt,
            history,
            None,  # No tools for planning
        )

        content = response.get("content", "")
        tool_calls = response.get("tool_calls", [])

        return ReActStep(
            step_number=len(self._steps) + 1,
            step_type=StepType.PLAN,
            content=content,
            tool_calls=tool_calls,
            metadata={"prompt": prompt},
        )

    async def _act(
        self,
        plan_step: ReActStep,
        context: Dict[str, Any],
    ) -> ReActStep:
        """Execute the planned actions."""
        tool_calls = plan_step.tool_calls

        if not tool_calls:
            return ReActStep(
                step_number=len(self._steps) + 1,
                step_type=StepType.ACTION,
                content="No actions to execute",
                metadata={"action_count": 0},
            )

        # Create execution context
        exec_context = ExecutionContext(
            session_id=context.get("session_id", "default"),
            agent_id=context.get("agent_id"),
            task_id=context.get("task_id"),
        )

        # Execute tools
        results = await self.tool_executor.execute_parallel(
            tool_calls,
            context=exec_context,
            stop_on_error=False,
        )

        # Extract results
        tool_results = [r.result for r in results]

        # Count errors
        error_count = sum(1 for r in tool_results if not r.success)

        content_lines = [f"Executed {len(tool_calls)} action(s):"]
        for call, result in zip(tool_calls, tool_results):
            status = "✓" if result.success else "✗"
            content_lines.append(f"  {status} {call.tool_name}")

        return ReActStep(
            step_number=len(self._steps) + 1,
            step_type=StepType.ACTION,
            content="\n".join(content_lines),
            tool_calls=tool_calls,
            tool_results=tool_results,
            metadata={
                "action_count": len(tool_calls),
                "success_count": len(tool_calls) - error_count,
                "error_count": error_count,
                "has_errors": error_count > 0,
            },
        )

    async def _observe(self, action_step: ReActStep) -> ReActStep:
        """Observe and summarize the results of actions."""
        tool_results = action_step.tool_results

        if not tool_results:
            return ReActStep(
                step_number=len(self._steps) + 1,
                step_type=StepType.OBSERVATION,
                content="No results to observe",
            )

        observations = []
        for i, result in enumerate(tool_results, 1):
            if result.success:
                observations.append(f"{i}. Success: {result.output}")
            else:
                observations.append(f"{i}. Error ({result.error_type}): {result.error}")

        content = "\n".join(observations)

        return ReActStep(
            step_number=len(self._steps) + 1,
            step_type=StepType.OBSERVATION,
            content=content,
            metadata={"observation_count": len(observations)},
        )

    async def _reflect(
        self,
        task: str,
        context: Dict[str, Any],
        history: List[Dict[str, Any]],
    ) -> ReActStep:
        """Reflect on progress and decide if task is complete."""
        prompt = self._build_reflection_prompt(task, context, history)

        response = await self.llm_generate(
            prompt,
            history,
            None,
        )

        content = response.get("content", "")

        # Parse reflection to check if task is complete
        task_complete = self._check_task_completion(content)

        return ReActStep(
            step_number=len(self._steps) + 1,
            step_type=StepType.REFLECTION,
            content=content,
            metadata={
                "task_complete": task_complete,
                "prompt": prompt,
            },
        )

    async def _generate_final_answer(
        self,
        task: str,
        history: List[Dict[str, Any]],
    ) -> ReActStep:
        """Generate the final answer based on all steps."""
        prompt = f"""Based on all the work done, provide a final answer to the task:

Task: {task}

Provide a clear, concise final answer that addresses the task."""

        response = await self.llm_generate(
            prompt,
            history,
            None,
        )

        content = response.get("content", "")

        return ReActStep(
            step_number=len(self._steps) + 1,
            step_type=StepType.FINAL_ANSWER,
            content=content,
        )

    def _build_thought_prompt(
        self,
        task: str,
        context: Dict[str, Any],
        history: List[Dict[str, Any]],
    ) -> str:
        """Build prompt for thought generation."""
        return f"""Analyze the current situation for this task:

Task: {task}

Think about:
1. What have we learned so far?
2. What information do we still need?
3. What challenges or obstacles exist?
4. What should we focus on next?

Provide your analysis:"""

    def _build_plan_prompt(
        self,
        task: str,
        context: Dict[str, Any],
        history: List[Dict[str, Any]],
    ) -> str:
        """Build prompt for plan generation."""
        return f"""Based on your analysis, create a plan for the next steps:

Task: {task}

What tools should we use and why? What specific actions will move us closer to completing the task?

Provide your plan:"""

    def _build_reflection_prompt(
        self,
        task: str,
        context: Dict[str, Any],
        history: List[Dict[str, Any]],
    ) -> str:
        """Build prompt for reflection."""
        return f"""Reflect on the progress made so far:

Task: {task}

Consider:
1. Did the recent actions help progress toward the goal?
2. Were there any errors or unexpected results?
3. Is the task complete, or is more work needed?
4. If more work is needed, what should we do differently?

Provide your reflection and indicate if the task is COMPLETE or INCOMPLETE:"""

    def _check_task_completion(self, reflection: str) -> bool:
        """Check if reflection indicates task is complete."""
        reflection_lower = reflection.lower()
        complete_keywords = ["complete", "finished", "done", "accomplished", "success"]
        incomplete_keywords = ["incomplete", "unfinished", "more work", "still need", "not done"]

        # Check for explicit completion markers
        if "task is complete" in reflection_lower or "task complete" in reflection_lower:
            return True
        if "task is incomplete" in reflection_lower or "task incomplete" in reflection_lower:
            return False

        # Count keywords
        complete_count = sum(1 for kw in complete_keywords if kw in reflection_lower)
        incomplete_count = sum(1 for kw in incomplete_keywords if kw in reflection_lower)

        return complete_count > incomplete_count

    def _build_conversation_history(self) -> List[Dict[str, Any]]:
        """Build conversation history from steps."""
        history = []
        for step in self._steps:
            history.append({
                "role": "assistant",
                "content": step.to_context_string(),
            })
        return history

    def get_steps(self) -> List[ReActStep]:
        """Get all steps from the loop."""
        return self._steps.copy()

    def get_step_count(self) -> int:
        """Get total step count."""
        return len(self._steps)

    def get_iteration_count(self) -> int:
        """Get current iteration count."""
        return self._current_iteration
