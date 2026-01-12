"""
Self-critique system for agents.
Allows agents to review and improve their own work.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class CritiqueAspect(str, Enum):
    """Aspects to critique."""
    CORRECTNESS = "correctness"
    COMPLETENESS = "completeness"
    EFFICIENCY = "efficiency"
    CLARITY = "clarity"
    SAFETY = "safety"
    BEST_PRACTICES = "best_practices"


class CritiqueSeverity(str, Enum):
    """Severity of critique issues."""
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    SUGGESTION = "suggestion"


@dataclass
class CritiqueIssue:
    """An issue found during critique."""
    aspect: CritiqueAspect
    severity: CritiqueSeverity
    description: str
    location: Optional[str] = None
    suggestion: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "aspect": self.aspect.value,
            "severity": self.severity.value,
            "description": self.description,
            "location": self.location,
            "suggestion": self.suggestion,
            "metadata": self.metadata,
        }


@dataclass
class CritiqueResult:
    """Result of a critique."""
    overall_quality: float  # 0-10 score
    issues: List[CritiqueIssue]
    strengths: List[str]
    suggestions_for_improvement: List[str]
    should_revise: bool
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "overall_quality": self.overall_quality,
            "issues": [issue.to_dict() for issue in self.issues],
            "issue_count": len(self.issues),
            "critical_issues": len([i for i in self.issues if i.severity == CritiqueSeverity.CRITICAL]),
            "major_issues": len([i for i in self.issues if i.severity == CritiqueSeverity.MAJOR]),
            "strengths": self.strengths,
            "suggestions_for_improvement": self.suggestions_for_improvement,
            "should_revise": self.should_revise,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }


# Type for LLM generation
LLMGenerateFunc = Callable[[str, Optional[List[Dict]]], Awaitable[str]]


class SelfCritique:
    """
    Self-critique system for agents.

    Allows agents to review their own work and identify issues.
    Uses LLM to perform structured critique across multiple aspects.

    Example:
        critique = SelfCritique(llm_generate=my_llm_function)

        result = await critique.critique_result(
            task="Find all Python files",
            result="Found 10 files: ...",
            aspects=[CritiqueAspect.CORRECTNESS, CritiqueAspect.COMPLETENESS]
        )

        if result.should_revise:
            # Revise the work based on suggestions
            pass
    """

    def __init__(
        self,
        llm_generate: LLMGenerateFunc,
        quality_threshold: float = 7.0,
        max_revisions: int = 3,
    ):
        """
        Initialize the self-critique system.

        Args:
            llm_generate: Function to generate LLM responses
            quality_threshold: Minimum quality score to accept (0-10)
            max_revisions: Maximum number of revision attempts
        """
        self.llm_generate = llm_generate
        self.quality_threshold = quality_threshold
        self.max_revisions = max_revisions

    async def critique_result(
        self,
        task: str,
        result: Any,
        aspects: Optional[List[CritiqueAspect]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> CritiqueResult:
        """
        Critique a task result.

        Args:
            task: The original task
            result: The result to critique
            aspects: Aspects to critique (defaults to all)
            context: Additional context

        Returns:
            CritiqueResult with issues and suggestions
        """
        aspects = aspects or list(CritiqueAspect)

        # Build critique prompt
        prompt = self._build_critique_prompt(task, result, aspects, context)

        # Generate critique
        response = await self.llm_generate(prompt, None)

        # Parse critique response
        critique_data = self._parse_critique_response(response)

        # Create result
        critique_result = CritiqueResult(
            overall_quality=critique_data.get("quality_score", 5.0),
            issues=critique_data.get("issues", []),
            strengths=critique_data.get("strengths", []),
            suggestions_for_improvement=critique_data.get("suggestions", []),
            should_revise=critique_data.get("quality_score", 5.0) < self.quality_threshold,
            metadata={
                "task": task,
                "aspects_critiqued": [a.value for a in aspects],
                "context": context,
            },
        )

        logger.info(
            f"Critique complete: quality={critique_result.overall_quality:.1f}, "
            f"issues={len(critique_result.issues)}, "
            f"should_revise={critique_result.should_revise}"
        )

        return critique_result

    async def critique_and_revise(
        self,
        task: str,
        initial_result: Any,
        revision_func: Callable[[CritiqueResult], Awaitable[Any]],
        aspects: Optional[List[CritiqueAspect]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Critique result and iteratively revise until quality threshold met.

        Args:
            task: The original task
            initial_result: Initial result to critique
            revision_func: Async function to revise based on critique
            aspects: Aspects to critique
            context: Additional context

        Returns:
            Dict with final result, critiques, and revision history
        """
        current_result = initial_result
        critiques = []
        revisions = []

        for revision_num in range(self.max_revisions + 1):
            # Critique current result
            critique = await self.critique_result(
                task, current_result, aspects, context
            )
            critiques.append(critique)

            # Check if quality is acceptable
            if not critique.should_revise or revision_num == self.max_revisions:
                break

            logger.info(f"Revision {revision_num + 1}/{self.max_revisions} needed")

            # Revise based on critique
            revised_result = await revision_func(critique)
            revisions.append({
                "revision_number": revision_num + 1,
                "original": current_result,
                "revised": revised_result,
                "critique": critique.to_dict(),
            })

            current_result = revised_result

        return {
            "final_result": current_result,
            "final_quality": critiques[-1].overall_quality,
            "critiques": [c.to_dict() for c in critiques],
            "revisions": revisions,
            "revision_count": len(revisions),
            "quality_threshold_met": critiques[-1].overall_quality >= self.quality_threshold,
        }

    async def critique_code(
        self,
        code: str,
        language: str = "python",
        context: Optional[str] = None,
    ) -> CritiqueResult:
        """
        Critique code specifically.

        Args:
            code: The code to critique
            language: Programming language
            context: Additional context about the code

        Returns:
            CritiqueResult with code-specific feedback
        """
        prompt = f"""Review this {language} code for quality and best practices.

{f'Context: {context}' if context else ''}

Code:
```{language}
{code}
```

Critique the code across these aspects:
1. Correctness: Does it work as intended?
2. Safety: Any security vulnerabilities or dangerous operations?
3. Best Practices: Does it follow {language} conventions?
4. Efficiency: Are there performance issues?
5. Clarity: Is it readable and well-structured?

Provide:
- Overall quality score (0-10)
- List of issues with severity (critical/major/minor/suggestion)
- Strengths of the code
- Specific suggestions for improvement

Format your response clearly."""

        response = await self.llm_generate(prompt, None)

        critique_data = self._parse_critique_response(response)

        return CritiqueResult(
            overall_quality=critique_data.get("quality_score", 5.0),
            issues=critique_data.get("issues", []),
            strengths=critique_data.get("strengths", []),
            suggestions_for_improvement=critique_data.get("suggestions", []),
            should_revise=critique_data.get("quality_score", 5.0) < self.quality_threshold,
            metadata={
                "language": language,
                "context": context,
                "code_length": len(code),
            },
        )

    def _build_critique_prompt(
        self,
        task: str,
        result: Any,
        aspects: List[CritiqueAspect],
        context: Optional[Dict[str, Any]],
    ) -> str:
        """Build critique prompt."""
        aspect_descriptions = {
            CritiqueAspect.CORRECTNESS: "Is the result correct and accurate?",
            CritiqueAspect.COMPLETENESS: "Does it fully address the task?",
            CritiqueAspect.EFFICIENCY: "Is it efficient and optimized?",
            CritiqueAspect.CLARITY: "Is it clear and well-presented?",
            CritiqueAspect.SAFETY: "Is it safe and without risks?",
            CritiqueAspect.BEST_PRACTICES: "Does it follow best practices?",
        }

        prompt = f"""Critique the following result for the given task.

Task: {task}

Result:
{result}
"""

        if context:
            prompt += f"\nContext: {context}\n"

        prompt += "\nCritique across these aspects:\n"
        for aspect in aspects:
            prompt += f"- {aspect.value}: {aspect_descriptions[aspect]}\n"

        prompt += """
Provide a structured critique:
1. Overall quality score (0-10)
2. Issues found (with severity: critical, major, minor, or suggestion)
3. Strengths of the result
4. Specific suggestions for improvement

Be thorough and specific in your critique."""

        return prompt

    def _parse_critique_response(self, response: str) -> Dict[str, Any]:
        """Parse critique response from LLM."""
        import re

        result = {
            "quality_score": 5.0,
            "issues": [],
            "strengths": [],
            "suggestions": [],
        }

        # Extract quality score
        score_match = re.search(r'(?:quality|score)[:\s]+(\d+(?:\.\d+)?)', response, re.IGNORECASE)
        if score_match:
            result["quality_score"] = float(score_match.group(1))

        # Extract issues
        issue_patterns = [
            r'(?:critical|major|minor|suggestion)[:\s]*(.+?)(?=(?:critical|major|minor|suggestion|strength|suggestion for improvement)|$)',
        ]

        for pattern in issue_patterns:
            matches = re.finditer(pattern, response, re.IGNORECASE | re.DOTALL)
            for match in matches:
                issue_text = match.group(0).strip()
                severity = self._determine_severity(issue_text)
                description = match.group(1).strip()

                if description:
                    result["issues"].append(
                        CritiqueIssue(
                            aspect=CritiqueAspect.CORRECTNESS,  # Default
                            severity=severity,
                            description=description,
                        )
                    )

        # Extract strengths
        strengths_match = re.search(
            r'strengths?[:\s]+((?:.+\n?)+?)(?=suggestions?|issues?|$)',
            response,
            re.IGNORECASE
        )
        if strengths_match:
            strengths_text = strengths_match.group(1)
            result["strengths"] = [
                s.strip('- \n') for s in strengths_text.split('\n')
                if s.strip() and not s.strip().startswith(('1.', '2.', 'suggestions', 'issues'))
            ]

        # Extract suggestions
        suggestions_match = re.search(
            r'suggestions?(?:\s+for\s+improvement)?[:\s]+((?:.+\n?)+?)$',
            response,
            re.IGNORECASE
        )
        if suggestions_match:
            suggestions_text = suggestions_match.group(1)
            result["suggestions"] = [
                s.strip('- \n') for s in suggestions_text.split('\n')
                if s.strip() and len(s.strip()) > 10
            ]

        return result

    def _determine_severity(self, text: str) -> CritiqueSeverity:
        """Determine issue severity from text."""
        text_lower = text.lower()

        if "critical" in text_lower:
            return CritiqueSeverity.CRITICAL
        elif "major" in text_lower:
            return CritiqueSeverity.MAJOR
        elif "minor" in text_lower:
            return CritiqueSeverity.MINOR
        else:
            return CritiqueSeverity.SUGGESTION
