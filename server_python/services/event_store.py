"""
Event Store - All events go through here before WebSocket broadcast
Provides event replay capability for reconnection and audit logging
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from services.redis_service import redis_service


class EventStore:
    """
    Event store with Redis backend
    Single source of truth for all system events
    """

    def __init__(self, redis_client=None):
        """
        Initialize event store
        Args:
            redis_client: Optional redis service instance (defaults to global singleton)
        """
        self.redis_service = redis_client or redis_service

    async def store_event(self, event_type: str, payload: Dict[str, Any]) -> float:
        """
        Store event to global timeline and task-specific stream if applicable

        Args:
            event_type: Type of event (e.g., "agent_update", "task_interaction")
            payload: Event data

        Returns:
            timestamp (milliseconds) for client cursor tracking
        """
        # Build complete event with metadata
        event = {
            "type": event_type,
            "payload": payload,
            "timestamp": datetime.now().isoformat()
        }

        # Store to global timeline
        timestamp = await self.redis_service.add_event(event)

        # If event is task-specific, also add to task stream
        task_id = self._extract_task_id(event_type, payload)
        if task_id:
            await self.redis_service.add_task_event(task_id, event)

        return timestamp

    async def get_events_since(self, timestamp_ms: float, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Get events since timestamp (for reconnection replay)

        Args:
            timestamp_ms: Unix timestamp in milliseconds
            limit: Maximum number of events to return

        Returns:
            List of events ordered by timestamp
        """
        return await self.redis_service.get_events_since(timestamp_ms, limit)

    async def get_recent_events(self, count: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent events (for initial connection)

        Args:
            count: Number of recent events to return

        Returns:
            List of events in reverse chronological order
        """
        return await self.redis_service.get_recent_events(count)

    async def get_task_events(self, task_id: str, since_id: str = "-") -> List[Dict[str, Any]]:
        """
        Get all events for specific task

        Args:
            task_id: Task identifier
            since_id: Stream ID to start from ("-" for all events)

        Returns:
            List of task-specific events
        """
        return await self.redis_service.get_task_events(task_id, since_id)

    async def get_agent_events(self, agent_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get events related to specific agent
        Filters global timeline by agent_id

        Args:
            agent_id: Agent identifier
            limit: Maximum number of events

        Returns:
            List of agent-related events
        """
        # Get recent events and filter by agent_id
        all_events = await self.get_recent_events(limit * 2)  # Get more to account for filtering

        agent_events = []
        for event in all_events:
            payload = event.get("payload", {})
            # Check if event is related to this agent
            if (payload.get("agentId") == agent_id or
                    payload.get("agent_id") == agent_id or
                    payload.get("id") == agent_id):
                agent_events.append(event)
                if len(agent_events) >= limit:
                    break

        return agent_events

    def _extract_task_id(self, event_type: str, payload: Dict[str, Any]) -> Optional[str]:
        """
        Extract task_id from payload if present

        Args:
            event_type: Type of event
            payload: Event data

        Returns:
            task_id if found, None otherwise
        """
        # Direct task_id fields
        task_id_fields = ["taskId", "task_id", "relatedTaskId"]
        for field in task_id_fields:
            if field in payload:
                return payload[field]

        # Nested task_id (e.g., in task object)
        if isinstance(payload, dict):
            for value in payload.values():
                if isinstance(value, dict):
                    for field in task_id_fields:
                        if field in value:
                            return value[field]

        # Event type-specific extraction
        if event_type == "task_created" and "id" in payload:
            return payload["id"]
        elif event_type == "task_updated" and "id" in payload:
            return payload["id"]

        return None

    async def cleanup_old_events(self, days: int = 7):
        """
        Remove events older than specified days
        Helps manage Redis memory usage

        Args:
            days: Number of days to retain events

        Returns:
            Number of events removed
        """
        return await self.redis_service.cleanup_old_events(days)

    async def get_event_stats(self) -> Dict[str, Any]:
        """
        Get event store statistics

        Returns:
            Dict with event counts and metadata
        """
        stats = await self.redis_service.get_stats()
        return {
            "total_events": stats.get("total_events", 0),
            "task_streams": stats.get("task_streams", 0),
            "active_workflows": stats.get("active_workflows", 0),
            "registered_agents": stats.get("registered_agents", 0),
            "connected_clients": stats.get("connected_clients", 0),
        }


# Global singleton instance
event_store = EventStore()
