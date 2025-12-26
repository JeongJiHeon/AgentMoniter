"""
Redis Connection Test Script
Run this to verify Redis is working correctly
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.redis_service import redis_service
from services.event_store import event_store


async def test_redis_connection():
    """Test Redis connection and basic operations"""
    print("=" * 60)
    print("Redis Connection Test")
    print("=" * 60)

    try:
        # Test 1: Connect to Redis
        print("\n[Test 1] Connecting to Redis...")
        await redis_service.connect()
        print("✅ Successfully connected to Redis")

        # Test 2: Health check
        print("\n[Test 2] Health check...")
        is_healthy = await redis_service.health_check()
        if is_healthy:
            print("✅ Redis is healthy")
        else:
            print("❌ Redis health check failed")
            return

        # Test 3: Store and retrieve event
        print("\n[Test 3] Storing test event...")
        test_event = {
            "type": "test_event",
            "payload": {
                "message": "Hello from Redis!",
                "timestamp": "2025-12-26T13:00:00Z"
            },
            "test": True
        }
        timestamp = await event_store.store_event("test_event", test_event["payload"])
        print(f"✅ Event stored with timestamp: {timestamp}")

        # Test 4: Retrieve recent events
        print("\n[Test 4] Retrieving recent events...")
        recent_events = await event_store.get_recent_events(count=10)
        print(f"✅ Retrieved {len(recent_events)} events")
        if recent_events:
            print(f"   Latest event type: {recent_events[0].get('type')}")

        # Test 5: Workflow state operations
        print("\n[Test 5] Testing workflow state...")
        test_workflow = {
            "task_id": "test-task-123",
            "status": "running",
            "current_step_index": 0,
            "steps": [{"id": "step1", "name": "Test Step"}]
        }
        await redis_service.save_workflow_state("test-task-123", test_workflow)
        print("✅ Workflow state saved")

        retrieved_workflow = await redis_service.get_workflow_state("test-task-123")
        if retrieved_workflow and retrieved_workflow.get("status") == "running":
            print("✅ Workflow state retrieved correctly")
        else:
            print("❌ Workflow state retrieval failed")

        # Test 6: Agent state operations
        print("\n[Test 6] Testing agent state...")
        test_agent = {
            "id": "test-agent-123",
            "name": "Test Agent",
            "status": "IDLE",
            "lifecycle_status": "IDLE"
        }
        await redis_service.save_agent_state("test-agent-123", test_agent)
        print("✅ Agent state saved")

        retrieved_agent = await redis_service.get_agent_state("test-agent-123")
        if retrieved_agent and retrieved_agent.get("name") == "Test Agent":
            print("✅ Agent state retrieved correctly")
        else:
            print("❌ Agent state retrieval failed")

        # Test 7: Get statistics
        print("\n[Test 7] Getting Redis statistics...")
        stats = await redis_service.get_stats()
        print(f"✅ Statistics retrieved:")
        print(f"   Total events: {stats.get('total_events', 0)}")
        print(f"   Active workflows: {stats.get('active_workflows', 0)}")
        print(f"   Registered agents: {stats.get('registered_agents', 0)}")

        # Cleanup test data
        print("\n[Cleanup] Removing test data...")
        await redis_service.delete_workflow_state("test-task-123")
        await redis_service.delete_agent_state("test-agent-123")
        print("✅ Test data cleaned up")

        print("\n" + "=" * 60)
        print("✅ All tests passed! Redis is working correctly.")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Disconnect
        print("\n[Final] Disconnecting from Redis...")
        await redis_service.disconnect()
        print("✅ Disconnected")


if __name__ == "__main__":
    print("\nMake sure Redis is running:")
    print("  docker-compose up -d")
    print("\nStarting tests...\n")

    asyncio.run(test_redis_connection())
