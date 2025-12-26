"""
Redis Service - Central Redis connection and operations
Provides event storage, workflow state management, and agent state tracking
"""
import redis.asyncio as redis
import json
import time
from typing import Optional, Dict, Any, List
from datetime import datetime
import os


class RedisService:
    """
    Async Redis client with connection pooling
    Single source of truth for all state and events
    """

    def __init__(self, url: Optional[str] = None):
        self.url = url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.client: Optional[redis.Redis] = None
        self._max_connections = int(os.getenv("REDIS_MAX_CONNECTIONS", "50"))

    async def connect(self):
        """Initialize Redis connection pool"""
        try:
            self.client = await redis.from_url(
                self.url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=self._max_connections
            )
            # Test connection
            await self.client.ping()
            print(f"[Redis] Connected to {self.url}")
        except Exception as e:
            print(f"[Redis] Connection failed: {e}")
            raise

    async def disconnect(self):
        """Close Redis connection"""
        if self.client:
            await self.client.close()
            print("[Redis] Disconnected")

    async def health_check(self) -> bool:
        """Check if Redis is healthy"""
        try:
            if not self.client:
                return False
            await self.client.ping()
            return True
        except Exception:
            return False

    # ===== Event Timeline Operations =====

    async def add_event(self, event: Dict[str, Any]) -> float:
        """
        Add event to global timeline (sorted set)
        Returns: timestamp in milliseconds
        """
        timestamp = time.time() * 1000  # milliseconds
        event_json = json.dumps(event)
        await self.client.zadd("events:timeline", {event_json: timestamp})
        return timestamp

    async def get_events_since(self, timestamp_ms: float, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get events since timestamp (for reconnection replay)
        Args:
            timestamp_ms: Unix timestamp in milliseconds
            limit: Maximum number of events to return
        Returns: List of events ordered by timestamp
        """
        events = await self.client.zrangebyscore(
            "events:timeline",
            timestamp_ms,
            "+inf",
            start=0,
            num=limit
        )
        return [json.loads(e) for e in events]

    async def get_recent_events(self, count: int = 100) -> List[Dict[str, Any]]:
        """
        Get most recent events (for initial load)
        Returns events in reverse chronological order (newest first)
        """
        events = await self.client.zrevrange("events:timeline", 0, count - 1)
        return [json.loads(e) for e in events]

    async def cleanup_old_events(self, days: int = 7):
        """
        Remove events older than specified days
        Keeps timeline from growing indefinitely
        """
        cutoff_timestamp = (time.time() - (days * 24 * 3600)) * 1000
        removed = await self.client.zremrangebyscore("events:timeline", "-inf", cutoff_timestamp)
        print(f"[Redis] Cleaned up {removed} old events")
        return removed

    # ===== Task Event Stream Operations =====

    async def add_task_event(self, task_id: str, event: Dict[str, Any]) -> str:
        """
        Add event to task-specific stream
        Args:
            task_id: Task identifier
            event: Event data (will be flattened to string fields)
        Returns: Event ID from Redis stream
        """
        stream_key = f"task:{task_id}:events"
        # Flatten event dict to string fields for XADD
        event_fields = {}
        for key, value in event.items():
            if isinstance(value, (dict, list)):
                event_fields[key] = json.dumps(value)
            else:
                event_fields[key] = str(value)

        event_id = await self.client.xadd(stream_key, event_fields)
        # Set TTL on task stream (7 days)
        await self.client.expire(stream_key, 86400 * 7)
        return event_id

    async def get_task_events(self, task_id: str, since_id: str = "-") -> List[Dict[str, Any]]:
        """
        Get task events since specific ID
        Args:
            task_id: Task identifier
            since_id: Stream ID to start from ("-" for all events)
        Returns: List of events with parsed JSON fields
        """
        stream_key = f"task:{task_id}:events"
        events = await self.client.xrange(stream_key, since_id, "+")

        result = []
        for event_id, fields in events:
            # Parse JSON fields back to objects
            parsed = {"id": event_id}
            for key, value in fields.items():
                try:
                    parsed[key] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    parsed[key] = value
            result.append(parsed)

        return result

    # ===== Workflow State Operations =====

    async def save_workflow_state(self, task_id: str, workflow_state: Dict[str, Any]):
        """
        Save workflow state to Redis hash
        Complex fields (lists, dicts) are JSON-serialized
        """
        key = f"workflow:{task_id}"
        state_copy = workflow_state.copy()

        # Serialize complex fields
        for field_key in ["steps", "metadata"]:
            if field_key in state_copy and state_copy[field_key] is not None:
                state_copy[field_key] = json.dumps(state_copy[field_key])

        await self.client.hset(key, mapping=state_copy)
        # Set TTL: workflows expire after 24 hours of inactivity
        await self.client.expire(key, 86400)

    async def get_workflow_state(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get workflow state from Redis
        Returns: Workflow state dict or None if not found
        """
        key = f"workflow:{task_id}"
        state = await self.client.hgetall(key)

        if not state:
            return None

        # Deserialize JSON fields
        for field_key in ["steps", "metadata"]:
            if field_key in state and state[field_key]:
                try:
                    state[field_key] = json.loads(state[field_key])
                except (json.JSONDecodeError, TypeError):
                    pass

        return state

    async def delete_workflow_state(self, task_id: str):
        """Remove completed/cancelled workflow"""
        await self.client.delete(f"workflow:{task_id}")
        await self.client.delete(f"workflow:{task_id}:results")

    async def list_active_workflows(self) -> List[str]:
        """
        Get list of all active workflow task IDs
        Returns: List of task IDs
        """
        keys = await self.client.keys("workflow:*")
        # Extract task_id from keys (format: workflow:{task_id})
        task_ids = []
        for key in keys:
            if not key.endswith(":results"):
                task_id = key.replace("workflow:", "")
                task_ids.append(task_id)
        return task_ids

    # ===== Workflow Results Operations =====

    async def add_workflow_result(self, task_id: str, result: Dict[str, Any]):
        """Add step result to workflow results list"""
        key = f"workflow:{task_id}:results"
        await self.client.rpush(key, json.dumps(result))
        await self.client.expire(key, 86400)  # Match workflow TTL

    async def get_workflow_results(self, task_id: str) -> List[Dict[str, Any]]:
        """Get all step results for workflow"""
        key = f"workflow:{task_id}:results"
        results = await self.client.lrange(key, 0, -1)
        return [json.loads(r) for r in results]

    # ===== Agent State Operations =====

    async def save_agent_state(self, agent_id: str, state: Dict[str, Any]):
        """
        Save agent state to Redis hash
        Persists across server restarts (no TTL)
        """
        key = f"agent:{agent_id}"
        state_copy = state.copy()

        # Serialize complex fields
        if "conversation_context" in state_copy:
            state_copy["conversation_context"] = json.dumps(state_copy["conversation_context"])
        if "metadata" in state_copy:
            state_copy["metadata"] = json.dumps(state_copy["metadata"])

        await self.client.hset(key, mapping=state_copy)

    async def get_agent_state(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent state from Redis"""
        key = f"agent:{agent_id}"
        state = await self.client.hgetall(key)

        if not state:
            return None

        # Deserialize JSON fields
        if "conversation_context" in state and state["conversation_context"]:
            try:
                state["conversation_context"] = json.loads(state["conversation_context"])
            except (json.JSONDecodeError, TypeError):
                state["conversation_context"] = {}

        if "metadata" in state and state["metadata"]:
            try:
                state["metadata"] = json.loads(state["metadata"])
            except (json.JSONDecodeError, TypeError):
                state["metadata"] = {}

        return state

    async def get_all_agent_states(self) -> List[Dict[str, Any]]:
        """
        Get all agent states (for UI initial load)
        Returns: List of agent state dicts
        """
        keys = await self.client.keys("agent:*")
        agents = []

        for key in keys:
            state = await self.client.hgetall(key)
            if state:
                # Deserialize JSON fields
                if "conversation_context" in state and state["conversation_context"]:
                    try:
                        state["conversation_context"] = json.loads(state["conversation_context"])
                    except (json.JSONDecodeError, TypeError):
                        state["conversation_context"] = {}

                if "metadata" in state and state["metadata"]:
                    try:
                        state["metadata"] = json.loads(state["metadata"])
                    except (json.JSONDecodeError, TypeError):
                        state["metadata"] = {}

                agents.append(state)

        return agents

    async def delete_agent_state(self, agent_id: str):
        """Remove agent state"""
        await self.client.delete(f"agent:{agent_id}")

    # ===== Client Cursor Operations (for reconnection) =====

    async def save_client_cursor(self, client_id: str, cursor: str):
        """
        Save client's last seen event ID/timestamp
        TTL: 1 hour (enough for typical reconnection scenarios)
        """
        key = f"client:{client_id}:cursor"
        await self.client.set(key, cursor, ex=3600)

    async def get_client_cursor(self, client_id: str) -> Optional[str]:
        """Get client's last cursor for event replay"""
        key = f"client:{client_id}:cursor"
        return await self.client.get(key)

    async def delete_client_cursor(self, client_id: str):
        """Remove client cursor"""
        await self.client.delete(f"client:{client_id}:cursor")

    # ===== General Operations =====

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get Redis statistics for monitoring
        Returns: Dict with counts of various entities
        """
        stats = {
            "total_events": await self.client.zcard("events:timeline"),
            "active_workflows": len(await self.list_active_workflows()),
            "registered_agents": len(await self.client.keys("agent:*")),
            "connected_clients": len(await self.client.keys("client:*:cursor")),
            "task_streams": len(await self.client.keys("task:*:events")),
            "redis_memory_used": await self.client.info("memory"),
        }
        return stats


# Global singleton instance
redis_service = RedisService()
