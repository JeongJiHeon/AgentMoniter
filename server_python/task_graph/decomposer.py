"""
Task Decomposer for breaking down complex tasks into subtasks.
Uses LLM to intelligently decompose tasks and identify dependencies.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
import json
import re

from .dag import TaskGraph

logger = logging.getLogger(__name__)


class DecompositionStrategy(str, Enum):
    """Strategy for task decomposition."""
    SEQUENTIAL = "sequential"  # Tasks must run in order
    PARALLEL = "parallel"  # Tasks can run independently
    HYBRID = "hybrid"  # Mix of sequential and parallel
    AUTO = "auto"  # Let LLM decide


@dataclass
class SubTask:
    """A decomposed subtask."""
    name: str
    description: str
    dependencies: List[str] = field(default_factory=list)
    estimated_complexity: int = 1  # 1-10
    task_type: str = "generic"
    task_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "dependencies": self.dependencies,
            "estimated_complexity": self.estimated_complexity,
            "task_type": self.task_type,
            "task_data": self.task_data,
        }


@dataclass
class DecompositionResult:
    """Result of task decomposition."""
    original_task: str
    subtasks: List[SubTask]
    strategy: DecompositionStrategy
    rationale: str
    estimated_total_steps: int
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "original_task": self.original_task,
            "subtasks": [st.to_dict() for st in self.subtasks],
            "strategy": self.strategy.value,
            "rationale": self.rationale,
            "estimated_total_steps": self.estimated_total_steps,
            "metadata": self.metadata,
        }


# Type for LLM generation
LLMGenerateFunc = Callable[[str, Optional[List[Dict]]], Awaitable[str]]


class TaskDecomposer:
    """
    Decomposes complex tasks into subtasks with dependencies.

    Uses LLM to intelligently break down tasks and create a task graph.

    Example:
        decomposer = TaskDecomposer(llm_generate=my_llm_function)

        result = await decomposer.decompose(
            task="Build a web scraper for news articles",
            context={"language": "Python", "framework": "BeautifulSoup"}
        )

        # Create task graph
        graph = decomposer.create_task_graph(result)

        # Execute graph
        executor = GraphExecutor(graph)
        await executor.execute_all()
    """

    def __init__(
        self,
        llm_generate: LLMGenerateFunc,
        max_depth: int = 3,
        min_subtasks: int = 2,
        max_subtasks: int = 10,
    ):
        """
        Initialize the task decomposer.

        Args:
            llm_generate: Function to generate LLM responses
            max_depth: Maximum decomposition depth (recursive)
            min_subtasks: Minimum number of subtasks
            max_subtasks: Maximum number of subtasks
        """
        self.llm_generate = llm_generate
        self.max_depth = max_depth
        self.min_subtasks = min_subtasks
        self.max_subtasks = max_subtasks

    async def decompose(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        strategy: DecompositionStrategy = DecompositionStrategy.AUTO,
        depth: int = 0,
    ) -> DecompositionResult:
        """
        Decompose a task into subtasks.

        Args:
            task: The task to decompose
            context: Additional context
            strategy: Decomposition strategy
            depth: Current decomposition depth

        Returns:
            DecompositionResult with subtasks and dependencies
        """
        logger.info(f"Decomposing task (depth={depth}): {task[:100]}...")

        # Build decomposition prompt
        prompt = self._build_decomposition_prompt(task, context, strategy)

        # Generate decomposition
        response = await self.llm_generate(prompt, None)

        # Parse response
        subtasks = self._parse_decomposition_response(response)

        # Determine actual strategy used
        actual_strategy = self._infer_strategy(subtasks)

        # Calculate total steps
        total_steps = sum(st.estimated_complexity for st in subtasks)

        result = DecompositionResult(
            original_task=task,
            subtasks=subtasks,
            strategy=actual_strategy,
            rationale=self._extract_rationale(response),
            estimated_total_steps=total_steps,
            metadata={
                "context": context,
                "depth": depth,
                "llm_response": response,
            },
        )

        logger.info(
            f"Decomposed into {len(subtasks)} subtasks "
            f"(strategy={actual_strategy.value}, steps={total_steps})"
        )

        return result

    async def decompose_recursive(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        complexity_threshold: int = 5,
    ) -> DecompositionResult:
        """
        Recursively decompose complex tasks.

        Args:
            task: The task to decompose
            context: Additional context
            complexity_threshold: Complexity above which to decompose further

        Returns:
            DecompositionResult with fully decomposed hierarchy
        """
        # Initial decomposition
        result = await self.decompose(task, context, depth=0)

        # Recursively decompose complex subtasks
        for i, subtask in enumerate(result.subtasks):
            if (subtask.estimated_complexity > complexity_threshold and
                self.max_depth > 1):

                logger.debug(
                    f"Recursively decomposing complex subtask: {subtask.name}"
                )

                # Decompose this subtask
                sub_result = await self.decompose(
                    subtask.description,
                    context=context,
                    depth=1,
                )

                # Replace original subtask with decomposed subtasks
                # Update dependencies to point to first/last of sub-decomposition
                # (This is simplified - real implementation would be more complex)
                result.subtasks[i] = SubTask(
                    name=subtask.name,
                    description=f"Complex task decomposed into {len(sub_result.subtasks)} steps",
                    dependencies=subtask.dependencies,
                    estimated_complexity=len(sub_result.subtasks),
                    task_type="composite",
                    task_data={"subtasks": sub_result.to_dict()},
                )

        return result

    def create_task_graph(
        self,
        decomposition: DecompositionResult,
        graph_name: Optional[str] = None,
    ) -> TaskGraph:
        """
        Create a TaskGraph from decomposition result.

        Args:
            decomposition: The decomposition result
            graph_name: Optional name for the graph

        Returns:
            TaskGraph with all subtasks
        """
        graph = TaskGraph(name=graph_name or decomposition.original_task[:50])

        # Create mapping of subtask names to IDs
        name_to_id = {}

        # Add all subtasks to graph
        for subtask in decomposition.subtasks:
            # Resolve dependency IDs
            dep_ids = set()
            for dep_name in subtask.dependencies:
                if dep_name in name_to_id:
                    dep_ids.add(name_to_id[dep_name])
                else:
                    logger.warning(f"Dependency not found: {dep_name}")

            # Add task
            task_id = graph.add_task(
                name=subtask.name,
                description=subtask.description,
                dependencies=dep_ids,
                task_type=subtask.task_type,
                task_data=subtask.task_data,
                complexity=subtask.estimated_complexity,
            )

            name_to_id[subtask.name] = task_id

        logger.info(
            f"Created task graph '{graph.name}' with {len(decomposition.subtasks)} tasks"
        )

        return graph

    def _build_decomposition_prompt(
        self,
        task: str,
        context: Optional[Dict[str, Any]],
        strategy: DecompositionStrategy,
    ) -> str:
        """Build prompt for task decomposition."""
        prompt = f"""Decompose the following task into smaller, manageable subtasks.

Task: {task}
"""

        if context:
            prompt += f"\nContext: {json.dumps(context, indent=2)}\n"

        if strategy == DecompositionStrategy.SEQUENTIAL:
            prompt += "\nStrategy: Break into sequential steps that must be done in order.\n"
        elif strategy == DecompositionStrategy.PARALLEL:
            prompt += "\nStrategy: Break into independent tasks that can be done in parallel.\n"
        elif strategy == DecompositionStrategy.HYBRID:
            prompt += "\nStrategy: Mix of sequential and parallel tasks.\n"
        else:
            prompt += "\nStrategy: Automatically determine the best decomposition approach.\n"

        prompt += f"""
Requirements:
1. Create between {self.min_subtasks} and {self.max_subtasks} subtasks
2. Each subtask should be clear and actionable
3. Identify dependencies between subtasks
4. Estimate complexity for each subtask (1-10 scale)
5. Provide rationale for the decomposition approach

Format your response as JSON:
{{
  "rationale": "Why this decomposition makes sense...",
  "subtasks": [
    {{
      "name": "Subtask name",
      "description": "Detailed description",
      "dependencies": ["name of subtask this depends on"],
      "estimated_complexity": 5,
      "task_type": "generic|tool_call|llm_generation|research"
    }},
    ...
  ]
}}
"""

        return prompt

    def _parse_decomposition_response(self, response: str) -> List[SubTask]:
        """Parse LLM response into subtasks."""
        # Try to extract JSON
        try:
            # Look for JSON block
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group(0))
            else:
                data = json.loads(response)

            subtasks = []
            for st_data in data.get("subtasks", []):
                subtask = SubTask(
                    name=st_data.get("name", "Unnamed subtask"),
                    description=st_data.get("description", ""),
                    dependencies=st_data.get("dependencies", []),
                    estimated_complexity=st_data.get("estimated_complexity", 5),
                    task_type=st_data.get("task_type", "generic"),
                    task_data=st_data.get("task_data", {}),
                )
                subtasks.append(subtask)

            return subtasks

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON decomposition: {e}")

            # Fallback: Parse manually
            subtasks = self._parse_manual_decomposition(response)
            return subtasks

    def _parse_manual_decomposition(self, response: str) -> List[SubTask]:
        """Manually parse decomposition from text."""
        subtasks = []

        # Look for numbered lists
        pattern = r'(\d+)\.\s+([^\n]+)\n\s+Description:\s+([^\n]+)(?:\n\s+Dependencies:\s+([^\n]+))?'
        matches = re.finditer(pattern, response, re.MULTILINE)

        for match in matches:
            name = match.group(2).strip()
            description = match.group(3).strip()
            deps_str = match.group(4)
            dependencies = [d.strip() for d in deps_str.split(',')] if deps_str else []

            subtask = SubTask(
                name=name,
                description=description,
                dependencies=dependencies,
                estimated_complexity=5,  # Default
            )
            subtasks.append(subtask)

        if not subtasks:
            # Very simple fallback: split by newlines
            lines = [l.strip() for l in response.split('\n') if l.strip()]
            for i, line in enumerate(lines[:self.max_subtasks], 1):
                if len(line) > 10:  # Skip very short lines
                    subtasks.append(SubTask(
                        name=f"Step {i}",
                        description=line,
                        dependencies=[],
                        estimated_complexity=5,
                    ))

        return subtasks[:self.max_subtasks]

    def _extract_rationale(self, response: str) -> str:
        """Extract rationale from response."""
        # Try JSON first
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group(0))
                return data.get("rationale", "")
        except:
            pass

        # Look for "Rationale:" section
        rationale_match = re.search(
            r'rationale[:\s]+(.+?)(?=subtasks?|$)',
            response,
            re.IGNORECASE | re.DOTALL
        )

        if rationale_match:
            return rationale_match.group(1).strip()

        return "No rationale provided"

    def _infer_strategy(self, subtasks: List[SubTask]) -> DecompositionStrategy:
        """Infer decomposition strategy from subtasks."""
        if not subtasks:
            return DecompositionStrategy.SEQUENTIAL

        # Count dependencies
        has_deps = sum(1 for st in subtasks if st.dependencies)

        if has_deps == 0:
            return DecompositionStrategy.PARALLEL
        elif has_deps == len(subtasks) - 1:
            # Each task depends on previous (except first)
            return DecompositionStrategy.SEQUENTIAL
        else:
            return DecompositionStrategy.HYBRID
