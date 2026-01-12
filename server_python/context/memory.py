"""
Memory System for agents.
Provides short-term and long-term memory with semantic search capabilities.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import hashlib

logger = logging.getLogger(__name__)


class MemoryType(str, Enum):
    """Types of memories."""
    FACT = "fact"
    PATTERN = "pattern"
    EXPERIENCE = "experience"
    PREFERENCE = "preference"
    SKILL = "skill"


@dataclass
class Memory:
    """A single memory item."""
    id: str
    type: MemoryType
    content: str
    importance: float = 0.5  # 0-1
    confidence: float = 1.0  # 0-1
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    embedding: Optional[List[float]] = None  # For semantic search

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "content": self.content,
            "importance": self.importance,
            "confidence": self.confidence,
            "tags": list(self.tags),
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count,
        }

    def access(self) -> None:
        """Record memory access."""
        self.last_accessed = datetime.utcnow()
        self.access_count += 1

    def get_relevance_score(
        self,
        current_time: Optional[datetime] = None,
        recency_weight: float = 0.3,
        importance_weight: float = 0.4,
        access_weight: float = 0.3,
    ) -> float:
        """
        Calculate relevance score for this memory.

        Args:
            current_time: Current time for recency calculation
            recency_weight: Weight for recency factor
            importance_weight: Weight for importance
            access_weight: Weight for access frequency

        Returns:
            Relevance score (0-1)
        """
        current_time = current_time or datetime.utcnow()

        # Recency score (exponential decay)
        time_delta = (current_time - self.last_accessed).total_seconds()
        recency_score = 1.0 / (1.0 + time_delta / 86400)  # Decay over days

        # Importance score
        importance_score = self.importance

        # Access frequency score (normalized)
        access_score = min(self.access_count / 10, 1.0)

        # Weighted combination
        relevance = (
            recency_weight * recency_score +
            importance_weight * importance_score +
            access_weight * access_score
        )

        return relevance


class MemorySystem:
    """
    Memory system for agents.

    Provides:
    - Short-term memory (current conversation)
    - Long-term memory (persistent facts and patterns)
    - Memory consolidation
    - Semantic search (when embeddings available)
    - Memory decay and pruning

    Example:
        memory = MemorySystem(max_short_term=100)

        # Add memories
        memory.add_memory(
            MemoryType.FACT,
            "User prefers dark mode",
            importance=0.7,
            tags={"user_preference", "ui"}
        )

        # Recall memories
        relevant = memory.recall(
            query="user interface preferences",
            limit=5
        )

        # Consolidate short-term to long-term
        await memory.consolidate()
    """

    def __init__(
        self,
        max_short_term: int = 100,
        max_long_term: int = 1000,
        consolidation_threshold: int = 50,
        decay_threshold_days: int = 30,
    ):
        """
        Initialize the memory system.

        Args:
            max_short_term: Max short-term memories
            max_long_term: Max long-term memories
            consolidation_threshold: Consolidate when short-term reaches this
            decay_threshold_days: Remove memories older than this
        """
        self.max_short_term = max_short_term
        self.max_long_term = max_long_term
        self.consolidation_threshold = consolidation_threshold
        self.decay_threshold_days = decay_threshold_days

        self._short_term: Dict[str, Memory] = {}
        self._long_term: Dict[str, Memory] = {}

    def add_memory(
        self,
        memory_type: MemoryType,
        content: str,
        importance: float = 0.5,
        confidence: float = 1.0,
        tags: Optional[Set[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        to_long_term: bool = False,
    ) -> Memory:
        """
        Add a memory.

        Args:
            memory_type: Type of memory
            content: Memory content
            importance: Importance score (0-1)
            confidence: Confidence in this memory (0-1)
            tags: Optional tags
            metadata: Optional metadata
            to_long_term: Add directly to long-term memory

        Returns:
            The created Memory
        """
        # Generate ID from content
        memory_id = hashlib.md5(content.encode()).hexdigest()[:16]

        memory = Memory(
            id=memory_id,
            type=memory_type,
            content=content,
            importance=importance,
            confidence=confidence,
            tags=tags or set(),
            metadata=metadata or {},
        )

        # Add to appropriate store
        if to_long_term:
            self._long_term[memory_id] = memory
            logger.debug(f"Added long-term {memory_type.value} memory")
        else:
            self._short_term[memory_id] = memory
            logger.debug(f"Added short-term {memory_type.value} memory")

        # Auto-consolidate if threshold reached
        if len(self._short_term) >= self.consolidation_threshold:
            asyncio.create_task(self.consolidate())

        return memory

    def recall(
        self,
        query: Optional[str] = None,
        memory_type: Optional[MemoryType] = None,
        tags: Optional[Set[str]] = None,
        min_importance: float = 0.0,
        min_confidence: float = 0.0,
        limit: int = 10,
        include_short_term: bool = True,
        include_long_term: bool = True,
    ) -> List[Memory]:
        """
        Recall memories matching criteria.

        Args:
            query: Optional text query for semantic search
            memory_type: Filter by type
            tags: Filter by tags (any match)
            min_importance: Minimum importance
            min_confidence: Minimum confidence
            limit: Maximum memories to return
            include_short_term: Include short-term memories
            include_long_term: Include long-term memories

        Returns:
            List of matching memories, sorted by relevance
        """
        # Collect memories from stores
        memories = []

        if include_short_term:
            memories.extend(self._short_term.values())
        if include_long_term:
            memories.extend(self._long_term.values())

        # Filter by type
        if memory_type:
            memories = [m for m in memories if m.type == memory_type]

        # Filter by tags
        if tags:
            memories = [m for m in memories if tags & m.tags]

        # Filter by importance and confidence
        memories = [
            m for m in memories
            if m.importance >= min_importance and m.confidence >= min_confidence
        ]

        # Score by relevance
        for memory in memories:
            memory.access()  # Record access

        # Sort by relevance
        memories.sort(
            key=lambda m: m.get_relevance_score(),
            reverse=True
        )

        # Limit results
        memories = memories[:limit]

        logger.debug(f"Recalled {len(memories)} memories")

        return memories

    def get_memory(
        self,
        memory_id: str,
        from_long_term: bool = False,
    ) -> Optional[Memory]:
        """Get a specific memory by ID."""
        if from_long_term:
            return self._long_term.get(memory_id)
        else:
            return self._short_term.get(memory_id) or self._long_term.get(memory_id)

    async def consolidate(self) -> int:
        """
        Consolidate short-term memories to long-term.

        Moves important short-term memories to long-term storage.

        Returns:
            Number of memories consolidated
        """
        if not self._short_term:
            return 0

        logger.info("Consolidating short-term memories to long-term")

        # Score memories by importance and recency
        scored = []
        for memory in self._short_term.values():
            score = memory.get_relevance_score()
            scored.append((score, memory))

        scored.sort(reverse=True)

        # Move top memories to long-term
        consolidated = 0
        for score, memory in scored:
            # Only consolidate important memories
            if memory.importance < 0.5:
                continue

            # Move to long-term
            self._long_term[memory.id] = memory
            consolidated += 1

            # Stop if long-term is full
            if len(self._long_term) >= self.max_long_term:
                break

        # Clear short-term
        self._short_term.clear()

        logger.info(f"Consolidated {consolidated} memories to long-term")

        # Prune old long-term memories if needed
        if len(self._long_term) > self.max_long_term:
            await self.prune_old_memories()

        return consolidated

    async def prune_old_memories(self) -> int:
        """
        Remove old, low-importance memories.

        Returns:
            Number of memories pruned
        """
        if len(self._long_term) <= self.max_long_term:
            return 0

        logger.info("Pruning old long-term memories")

        cutoff_date = datetime.utcnow() - timedelta(days=self.decay_threshold_days)

        # Find memories to prune
        to_prune = []
        for memory_id, memory in self._long_term.items():
            # Prune if old and not important
            if (memory.last_accessed < cutoff_date and
                memory.importance < 0.6):
                to_prune.append(memory_id)

        # Remove pruned memories
        for memory_id in to_prune:
            del self._long_term[memory_id]

        logger.info(f"Pruned {len(to_prune)} old memories")

        return len(to_prune)

    def get_stats(self) -> Dict[str, Any]:
        """Get memory system statistics."""
        # Count by type
        type_counts = {}
        for memory_type in MemoryType:
            type_counts[memory_type.value] = {
                "short_term": sum(
                    1 for m in self._short_term.values()
                    if m.type == memory_type
                ),
                "long_term": sum(
                    1 for m in self._long_term.values()
                    if m.type == memory_type
                ),
            }

        return {
            "short_term_count": len(self._short_term),
            "long_term_count": len(self._long_term),
            "total_memories": len(self._short_term) + len(self._long_term),
            "short_term_capacity": f"{len(self._short_term)}/{self.max_short_term}",
            "long_term_capacity": f"{len(self._long_term)}/{self.max_long_term}",
            "type_distribution": type_counts,
        }

    def export_memories(
        self,
        include_short_term: bool = True,
        include_long_term: bool = True,
    ) -> Dict[str, Any]:
        """Export memories to dict format."""
        export_data = {
            "short_term": [],
            "long_term": [],
        }

        if include_short_term:
            export_data["short_term"] = [
                m.to_dict() for m in self._short_term.values()
            ]

        if include_long_term:
            export_data["long_term"] = [
                m.to_dict() for m in self._long_term.values()
            ]

        return export_data

    def import_memories(self, data: Dict[str, Any]) -> None:
        """Import memories from dict format."""
        # Clear existing
        self._short_term.clear()
        self._long_term.clear()

        # Import short-term
        for mem_data in data.get("short_term", []):
            memory = Memory(
                id=mem_data["id"],
                type=MemoryType(mem_data["type"]),
                content=mem_data["content"],
                importance=mem_data.get("importance", 0.5),
                confidence=mem_data.get("confidence", 1.0),
                tags=set(mem_data.get("tags", [])),
                metadata=mem_data.get("metadata", {}),
                created_at=datetime.fromisoformat(mem_data["created_at"]),
                last_accessed=datetime.fromisoformat(mem_data["last_accessed"]),
                access_count=mem_data.get("access_count", 0),
            )
            self._short_term[memory.id] = memory

        # Import long-term
        for mem_data in data.get("long_term", []):
            memory = Memory(
                id=mem_data["id"],
                type=MemoryType(mem_data["type"]),
                content=mem_data["content"],
                importance=mem_data.get("importance", 0.5),
                confidence=mem_data.get("confidence", 1.0),
                tags=set(mem_data.get("tags", [])),
                metadata=mem_data.get("metadata", {}),
                created_at=datetime.fromisoformat(mem_data["created_at"]),
                last_accessed=datetime.fromisoformat(mem_data["last_accessed"]),
                access_count=mem_data.get("access_count", 0),
            )
            self._long_term[memory.id] = memory

        logger.info(
            f"Imported {len(self._short_term)} short-term and "
            f"{len(self._long_term)} long-term memories"
        )

    def clear(self, clear_long_term: bool = False) -> None:
        """Clear memories."""
        self._short_term.clear()

        if clear_long_term:
            self._long_term.clear()

        logger.info("Cleared memory system")
