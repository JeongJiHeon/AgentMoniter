"""
Reasoning engines for agents.
Implements Chain-of-Thought and Tree-of-Thoughts patterns.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


# Type for LLM generation
LLMGenerateFunc = Callable[[str, Optional[List[Dict]]], Awaitable[str]]


class ReasoningStrategy(str, Enum):
    """Types of reasoning strategies."""
    DIRECT = "direct"
    CHAIN_OF_THOUGHT = "chain_of_thought"
    TREE_OF_THOUGHTS = "tree_of_thoughts"
    STEP_BY_STEP = "step_by_step"


@dataclass
class ThoughtNode:
    """A node in the thought tree."""
    id: str
    content: str
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "content": self.content,
            "parent_id": self.parent_id,
            "children": self.children,
            "score": self.score,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


class ReasoningEngine:
    """
    Base reasoning engine.
    Provides structured reasoning capabilities for agents.
    """

    def __init__(
        self,
        llm_generate: LLMGenerateFunc,
        strategy: ReasoningStrategy = ReasoningStrategy.CHAIN_OF_THOUGHT,
    ):
        """
        Initialize the reasoning engine.

        Args:
            llm_generate: Function to generate LLM responses
            strategy: Reasoning strategy to use
        """
        self.llm_generate = llm_generate
        self.strategy = strategy

    async def reason(
        self,
        problem: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Reason about a problem.

        Args:
            problem: The problem to reason about
            context: Additional context

        Returns:
            Dict with reasoning result
        """
        if self.strategy == ReasoningStrategy.CHAIN_OF_THOUGHT:
            engine = ChainOfThought(self.llm_generate)
            return await engine.reason(problem, context)
        elif self.strategy == ReasoningStrategy.TREE_OF_THOUGHTS:
            engine = TreeOfThoughts(self.llm_generate)
            return await engine.reason(problem, context)
        elif self.strategy == ReasoningStrategy.STEP_BY_STEP:
            engine = ChainOfThought(self.llm_generate)
            return await engine.reason_step_by_step(problem, context)
        else:
            # Direct reasoning
            response = await self.llm_generate(problem, None)
            return {
                "strategy": "direct",
                "result": response,
                "steps": [],
            }


class ChainOfThought:
    """
    Chain-of-Thought reasoning.
    Breaks down complex problems into sequential reasoning steps.
    """

    def __init__(self, llm_generate: LLMGenerateFunc):
        """Initialize CoT engine."""
        self.llm_generate = llm_generate

    async def reason(
        self,
        problem: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Perform chain-of-thought reasoning.

        Args:
            problem: The problem to reason about
            context: Additional context

        Returns:
            Dict with reasoning chain and final answer
        """
        prompt = f"""Let's solve this problem step by step.

Problem: {problem}

Think through this carefully, showing your reasoning at each step:"""

        if context:
            prompt += f"\n\nContext: {context}"

        # Generate reasoning chain
        response = await self.llm_generate(prompt, None)

        # Parse steps (simple heuristic: look for numbered steps)
        steps = self._parse_steps(response)

        return {
            "strategy": "chain_of_thought",
            "problem": problem,
            "reasoning_chain": response,
            "steps": steps,
            "step_count": len(steps),
        }

    async def reason_step_by_step(
        self,
        problem: str,
        context: Optional[Dict[str, Any]] = None,
        max_steps: int = 10,
    ) -> Dict[str, Any]:
        """
        Perform step-by-step reasoning with explicit control.

        Args:
            problem: The problem to reason about
            context: Additional context
            max_steps: Maximum reasoning steps

        Returns:
            Dict with detailed step-by-step reasoning
        """
        steps = []
        current_context = f"Problem: {problem}"

        if context:
            current_context += f"\nContext: {context}"

        for step_num in range(1, max_steps + 1):
            prompt = f"""{current_context}

Step {step_num}: What should we think about next? Provide one clear reasoning step:"""

            step_response = await self.llm_generate(prompt, None)
            steps.append({
                "step_number": step_num,
                "content": step_response,
            })

            # Check if reasoning is complete
            if self._is_reasoning_complete(step_response):
                break

            # Update context for next step
            current_context += f"\n\nStep {step_num}: {step_response}"

        # Generate final answer
        final_prompt = f"""{current_context}

Based on all the reasoning steps above, what is the final answer to the problem?"""

        final_answer = await self.llm_generate(final_prompt, None)

        return {
            "strategy": "step_by_step",
            "problem": problem,
            "steps": steps,
            "step_count": len(steps),
            "final_answer": final_answer,
        }

    def _parse_steps(self, text: str) -> List[str]:
        """Parse reasoning steps from text."""
        import re

        # Look for numbered steps
        pattern = r'(?:Step\s+)?(\d+)[.:)]?\s+(.+?)(?=(?:Step\s+)?\d+[.:)]|$)'
        matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)

        steps = []
        for match in matches:
            step_text = match.group(2).strip()
            if step_text:
                steps.append(step_text)

        # If no numbered steps found, split by newlines
        if not steps:
            steps = [line.strip() for line in text.split('\n') if line.strip()]

        return steps

    def _is_reasoning_complete(self, step_text: str) -> bool:
        """Check if reasoning appears complete."""
        completion_indicators = [
            "therefore",
            "in conclusion",
            "final answer",
            "the answer is",
            "we can conclude",
            "this gives us",
        ]

        step_lower = step_text.lower()
        return any(indicator in step_lower for indicator in completion_indicators)


class TreeOfThoughts:
    """
    Tree-of-Thoughts reasoning.
    Explores multiple reasoning paths and selects the best one.
    """

    def __init__(
        self,
        llm_generate: LLMGenerateFunc,
        branching_factor: int = 3,
        max_depth: int = 3,
    ):
        """
        Initialize ToT engine.

        Args:
            llm_generate: Function to generate LLM responses
            branching_factor: Number of alternative thoughts per node
            max_depth: Maximum depth of thought tree
        """
        self.llm_generate = llm_generate
        self.branching_factor = branching_factor
        self.max_depth = max_depth
        self._nodes: Dict[str, ThoughtNode] = {}
        self._node_counter = 0

    async def reason(
        self,
        problem: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Perform tree-of-thoughts reasoning.

        Args:
            problem: The problem to reason about
            context: Additional context

        Returns:
            Dict with thought tree and best path
        """
        self._nodes = {}
        self._node_counter = 0

        # Create root node
        root_id = self._create_node(problem, None)

        # Build thought tree
        await self._build_tree(root_id, depth=0, problem=problem, context=context)

        # Find best path
        best_path = self._find_best_path(root_id)

        # Generate final answer from best path
        path_summary = "\n\n".join([
            f"Step {i+1}: {self._nodes[node_id].content}"
            for i, node_id in enumerate(best_path)
        ])

        final_prompt = f"""Problem: {problem}

Reasoning path:
{path_summary}

Based on this reasoning, what is the final answer?"""

        final_answer = await self.llm_generate(final_prompt, None)

        return {
            "strategy": "tree_of_thoughts",
            "problem": problem,
            "thought_tree": {
                node_id: node.to_dict()
                for node_id, node in self._nodes.items()
            },
            "best_path": best_path,
            "best_path_thoughts": [self._nodes[nid].content for nid in best_path],
            "final_answer": final_answer,
            "total_nodes": len(self._nodes),
        }

    async def _build_tree(
        self,
        node_id: str,
        depth: int,
        problem: str,
        context: Optional[Dict[str, Any]],
    ) -> None:
        """Recursively build the thought tree."""
        if depth >= self.max_depth:
            return

        node = self._nodes[node_id]

        # Build context from path
        path_context = self._build_path_context(node_id, problem, context)

        # Generate alternative thoughts
        thoughts = await self._generate_alternative_thoughts(
            path_context,
            self.branching_factor
        )

        # Create child nodes
        for thought in thoughts:
            child_id = self._create_node(thought["content"], node_id)
            child_node = self._nodes[child_id]
            child_node.score = thought.get("score", 0.0)
            node.children.append(child_id)

        # Recursively expand most promising children
        if node.children:
            # Sort children by score
            sorted_children = sorted(
                node.children,
                key=lambda cid: self._nodes[cid].score,
                reverse=True
            )

            # Expand top children (prune low-scoring branches)
            for child_id in sorted_children[:2]:  # Expand top 2
                await self._build_tree(child_id, depth + 1, problem, context)

    async def _generate_alternative_thoughts(
        self,
        context: str,
        num_alternatives: int,
    ) -> List[Dict[str, Any]]:
        """Generate alternative reasoning paths."""
        prompt = f"""{context}

Generate {num_alternatives} different ways to think about the next step.
For each alternative, rate its promise from 0-10.

Provide alternatives:"""

        response = await self.llm_generate(prompt, None)

        # Parse alternatives (simple parsing)
        thoughts = []
        import re
        alt_pattern = r'Alternative\s+\d+:(.+?)(?:Score|Rating)[:\s]+(\d+)'
        matches = re.finditer(alt_pattern, response, re.IGNORECASE | re.DOTALL)

        for match in matches:
            content = match.group(1).strip()
            score = float(match.group(2))
            thoughts.append({"content": content, "score": score})

        # If parsing failed, create generic alternatives
        if not thoughts:
            thoughts = [{"content": response, "score": 5.0}]

        return thoughts[:num_alternatives]

    def _create_node(self, content: str, parent_id: Optional[str]) -> str:
        """Create a new thought node."""
        node_id = f"node_{self._node_counter}"
        self._node_counter += 1

        node = ThoughtNode(
            id=node_id,
            content=content,
            parent_id=parent_id,
        )

        self._nodes[node_id] = node
        return node_id

    def _build_path_context(
        self,
        node_id: str,
        problem: str,
        context: Optional[Dict[str, Any]],
    ) -> str:
        """Build context string from root to node."""
        path = []
        current_id = node_id

        while current_id:
            node = self._nodes[current_id]
            path.insert(0, node.content)
            current_id = node.parent_id

        context_str = f"Problem: {problem}\n\n"
        if context:
            context_str += f"Context: {context}\n\n"

        context_str += "Reasoning so far:\n"
        for i, thought in enumerate(path, 1):
            context_str += f"{i}. {thought}\n"

        return context_str

    def _find_best_path(self, root_id: str) -> List[str]:
        """Find the path with highest cumulative score."""
        def get_path_score(node_id: str) -> float:
            """Get cumulative score for a path."""
            score = 0.0
            current_id = node_id

            while current_id:
                node = self._nodes[current_id]
                score += node.score
                current_id = node.parent_id

            return score

        def get_leaf_nodes() -> List[str]:
            """Get all leaf nodes."""
            return [
                node_id for node_id, node in self._nodes.items()
                if not node.children
            ]

        # Find leaf with best path score
        leaves = get_leaf_nodes()
        if not leaves:
            return [root_id]

        best_leaf = max(leaves, key=get_path_score)

        # Build path from root to best leaf
        path = []
        current_id = best_leaf

        while current_id:
            path.insert(0, current_id)
            node = self._nodes[current_id]
            current_id = node.parent_id

        return path
