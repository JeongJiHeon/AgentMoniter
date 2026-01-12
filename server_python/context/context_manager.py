"""
Context Manager for handling conversation context and token limits.
Implements sliding window, summarization, and context compression strategies.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import tiktoken

logger = logging.getLogger(__name__)


class MessageRole(str, Enum):
    """Message roles in conversation."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    """A message in the conversation."""
    role: MessageRole
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    token_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "role": self.role.value,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "token_count": self.token_count,
        }


@dataclass
class ContextWindow:
    """Represents the current context window."""
    messages: List[Message]
    total_tokens: int
    max_tokens: int
    summarized_messages: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "message_count": len(self.messages),
            "total_tokens": self.total_tokens,
            "max_tokens": self.max_tokens,
            "token_usage_percent": round((self.total_tokens / self.max_tokens) * 100, 2),
            "summarized_messages": self.summarized_messages,
            "metadata": self.metadata,
        }


# Type for summarization function
SummarizeFunc = Callable[[List[Message]], Awaitable[str]]


class ContextManager:
    """
    Manages conversation context with token limits and compression.

    Features:
    - Token counting and limit enforcement
    - Sliding window for context management
    - Automatic summarization of old context
    - Context compression strategies

    Example:
        manager = ContextManager(
            max_tokens=100000,
            summarize_func=my_summarizer
        )

        # Add messages
        manager.add_message(MessageRole.USER, "Hello")
        manager.add_message(MessageRole.ASSISTANT, "Hi! How can I help?")

        # Get context for LLM
        context = manager.get_context_window()

        # Auto-summarize if needed
        await manager.maybe_summarize()
    """

    def __init__(
        self,
        max_tokens: int = 100000,
        summarize_threshold: float = 0.75,  # Summarize at 75% full
        summarize_func: Optional[SummarizeFunc] = None,
        model: str = "claude-3-5-sonnet-20241022",
        preserve_recent_messages: int = 10,
    ):
        """
        Initialize the context manager.

        Args:
            max_tokens: Maximum context tokens
            summarize_threshold: Fraction of max at which to summarize
            summarize_func: Async function to summarize messages
            model: Model name for token counting
            preserve_recent_messages: Number of recent messages to always keep
        """
        self.max_tokens = max_tokens
        self.summarize_threshold = summarize_threshold
        self.summarize_func = summarize_func
        self.model = model
        self.preserve_recent_messages = preserve_recent_messages

        self._messages: List[Message] = []
        self._summary: Optional[str] = None
        self._summarized_count = 0

        # Initialize tokenizer
        try:
            self._tokenizer = tiktoken.encoding_for_model("gpt-4")  # Use GPT-4 as proxy
        except:
            self._tokenizer = tiktoken.get_encoding("cl100k_base")

    def add_message(
        self,
        role: MessageRole,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Message:
        """
        Add a message to the context.

        Args:
            role: Message role
            content: Message content
            metadata: Optional metadata

        Returns:
            The created Message
        """
        message = Message(
            role=role,
            content=content,
            metadata=metadata or {},
            token_count=self._count_tokens(content),
        )

        self._messages.append(message)

        logger.debug(
            f"Added {role.value} message ({message.token_count} tokens)"
        )

        return message

    def add_messages(self, messages: List[Dict[str, Any]]) -> None:
        """Add multiple messages from dict format."""
        for msg in messages:
            self.add_message(
                MessageRole(msg.get("role", "user")),
                msg.get("content", ""),
                msg.get("metadata"),
            )

    def get_context_window(
        self,
        include_summary: bool = True,
    ) -> ContextWindow:
        """
        Get the current context window.

        Args:
            include_summary: Whether to include summary if available

        Returns:
            ContextWindow with messages
        """
        messages = self._messages.copy()
        total_tokens = sum(m.token_count for m in messages)

        # Add summary if available and requested
        if include_summary and self._summary:
            summary_msg = Message(
                role=MessageRole.SYSTEM,
                content=f"[Context Summary]\n{self._summary}",
                token_count=self._count_tokens(self._summary),
                metadata={"is_summary": True},
            )
            messages.insert(0, summary_msg)
            total_tokens += summary_msg.token_count

        return ContextWindow(
            messages=messages,
            total_tokens=total_tokens,
            max_tokens=self.max_tokens,
            summarized_messages=self._summarized_count,
        )

    def get_messages_for_llm(
        self,
        include_summary: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Get messages in LLM-compatible format.

        Args:
            include_summary: Whether to include summary

        Returns:
            List of message dicts
        """
        window = self.get_context_window(include_summary)
        return [
            {"role": msg.role.value, "content": msg.content}
            for msg in window.messages
        ]

    async def maybe_summarize(self) -> bool:
        """
        Summarize context if threshold is reached.

        Returns:
            True if summarization occurred
        """
        if not self.summarize_func:
            return False

        window = self.get_context_window(include_summary=False)

        # Check if we should summarize
        usage = window.total_tokens / window.max_tokens
        if usage < self.summarize_threshold:
            return False

        logger.info(
            f"Context usage at {usage:.1%}, triggering summarization"
        )

        # Determine how many messages to summarize
        # Keep recent messages intact
        if len(self._messages) <= self.preserve_recent_messages:
            logger.warning("Not enough messages to summarize")
            return False

        # Summarize all but recent messages
        messages_to_summarize = self._messages[:-self.preserve_recent_messages]
        messages_to_keep = self._messages[-self.preserve_recent_messages:]

        # Generate summary
        summary = await self.summarize_func(messages_to_summarize)

        # Update state
        self._summary = summary
        self._summarized_count += len(messages_to_summarize)
        self._messages = messages_to_keep

        logger.info(
            f"Summarized {len(messages_to_summarize)} messages, "
            f"keeping {len(messages_to_keep)} recent"
        )

        return True

    def compress_context(
        self,
        target_tokens: Optional[int] = None,
    ) -> int:
        """
        Compress context by removing old messages.

        Args:
            target_tokens: Target token count (defaults to max_tokens)

        Returns:
            Number of messages removed
        """
        target = target_tokens or self.max_tokens

        window = self.get_context_window(include_summary=False)
        if window.total_tokens <= target:
            return 0

        removed = 0

        # Remove oldest messages (except system messages) until under target
        while window.total_tokens > target and len(self._messages) > self.preserve_recent_messages:
            # Find oldest non-system message
            for i, msg in enumerate(self._messages):
                if msg.role != MessageRole.SYSTEM:
                    self._messages.pop(i)
                    self._summarized_count += 1
                    removed += 1
                    break

            window = self.get_context_window(include_summary=False)

        logger.info(f"Compressed context: removed {removed} messages")
        return removed

    def clear(self, keep_summary: bool = True) -> None:
        """
        Clear all messages.

        Args:
            keep_summary: Whether to keep the summary
        """
        self._messages.clear()

        if not keep_summary:
            self._summary = None
            self._summarized_count = 0

        logger.info("Cleared context")

    def get_stats(self) -> Dict[str, Any]:
        """Get context statistics."""
        window = self.get_context_window(include_summary=True)

        role_counts = {}
        for role in MessageRole:
            role_counts[role.value] = sum(
                1 for m in self._messages
                if m.role == role
            )

        return {
            "total_messages": len(self._messages),
            "total_tokens": window.total_tokens,
            "max_tokens": self.max_tokens,
            "usage_percent": round((window.total_tokens / self.max_tokens) * 100, 2),
            "summarized_messages": self._summarized_count,
            "has_summary": self._summary is not None,
            "role_distribution": role_counts,
        }

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        try:
            return len(self._tokenizer.encode(text))
        except Exception as e:
            logger.warning(f"Failed to count tokens: {e}")
            # Rough estimate: ~4 chars per token
            return len(text) // 4

    def export_history(self) -> List[Dict[str, Any]]:
        """Export full message history."""
        history = []

        if self._summary:
            history.append({
                "role": "system",
                "content": f"[Summary of {self._summarized_count} previous messages]\n{self._summary}",
                "is_summary": True,
            })

        for msg in self._messages:
            history.append(msg.to_dict())

        return history

    def import_history(self, history: List[Dict[str, Any]]) -> None:
        """Import message history."""
        self.clear()

        for msg_data in history:
            if msg_data.get("is_summary"):
                self._summary = msg_data["content"]
                continue

            self.add_message(
                MessageRole(msg_data["role"]),
                msg_data["content"],
                msg_data.get("metadata"),
            )
