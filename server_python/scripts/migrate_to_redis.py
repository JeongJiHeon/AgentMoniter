"""
Migration script: JSON file storage → Redis
Run this once to migrate existing agent data to Redis
"""
import asyncio
import json
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.redis_service import redis_service


async def load_agents_from_json():
    """Load agents from JSON file"""
    json_path = Path(__file__).parent.parent / "data" / "agents.json"

    if not json_path.exists():
        print(f"[Migration] JSON file not found: {json_path}")
        return []

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            agents = data.get("agents", [])
            print(f"[Migration] Loaded {len(agents)} agents from {json_path}")
            return agents
    except Exception as e:
        print(f"[Migration] Error loading JSON: {e}")
        return []


async def migrate_agents_to_redis(agents):
    """Migrate agents to Redis"""
    migrated_count = 0

    for agent_data in agents:
        agent_id = agent_data.get("id")
        if not agent_id:
            print(f"[Migration] Skipping agent without ID: {agent_data.get('name', 'Unknown')}")
            continue

        # Convert JSON agent to Redis format
        redis_state = {
            "id": agent_id,
            "name": agent_data.get("name", ""),
            "type": agent_data.get("type", "custom"),
            "status": "IDLE",
            "lifecycle_status": "IDLE",
            "last_activity": agent_data.get("updatedAt", agent_data.get("createdAt", "")),
            "conversation_context": json.dumps({}),
            "metadata": json.dumps({
                "createdAt": agent_data.get("createdAt"),
                "updatedAt": agent_data.get("updatedAt"),
                "description": agent_data.get("description", ""),
                "systemPrompt": agent_data.get("systemPrompt", ""),
                "constraints": agent_data.get("constraints", []),
                "allowedMCPs": agent_data.get("allowedMCPs", []),
                "isActive": agent_data.get("isActive", True)
            })
        }

        # Save to Redis
        await redis_service.save_agent_state(agent_id, redis_state)
        print(f"[Migration] ✅ Migrated agent: {agent_id} ({redis_state['name']})")
        migrated_count += 1

    return migrated_count


async def verify_migration():
    """Verify migration by reading back from Redis"""
    print("\n[Verification] Reading agents from Redis...")
    agents = await redis_service.get_all_agent_states()
    print(f"[Verification] Found {len(agents)} agents in Redis")

    for agent in agents:
        print(f"  - {agent.get('id')}: {agent.get('name')} (status: {agent.get('lifecycle_status')})")

    return len(agents)


async def migrate():
    """Main migration function"""
    print("=" * 70)
    print("Agent Monitor - JSON to Redis Migration Tool")
    print("=" * 70)

    try:
        # Step 1: Connect to Redis
        print("\n[Step 1/4] Connecting to Redis...")
        await redis_service.connect()

        # Check Redis health
        is_healthy = await redis_service.health_check()
        if not is_healthy:
            print("❌ Redis is not healthy. Please start Redis:")
            print("   docker-compose up -d")
            return

        print("✅ Connected to Redis")

        # Step 2: Load agents from JSON
        print("\n[Step 2/4] Loading agents from JSON file...")
        agents = await load_agents_from_json()

        if not agents:
            print("⚠️  No agents found in JSON file. Nothing to migrate.")
            print("   This is normal if you haven't created any custom agents yet.")
        else:
            # Step 3: Migrate to Redis
            print(f"\n[Step 3/4] Migrating {len(agents)} agents to Redis...")
            migrated_count = await migrate_agents_to_redis(agents)
            print(f"\n✅ Successfully migrated {migrated_count} agents")

        # Step 4: Verify
        print("\n[Step 4/4] Verifying migration...")
        redis_count = await verify_migration()

        # Summary
        print("\n" + "=" * 70)
        print("Migration Summary:")
        print(f"  - Agents in JSON: {len(agents)}")
        print(f"  - Agents migrated: {migrated_count if agents else 0}")
        print(f"  - Agents in Redis: {redis_count}")
        print("\n✅ Migration completed successfully!")
        print("=" * 70)

        # Next steps
        if agents:
            print("\n📝 Next Steps:")
            print("  1. Verify agents in Redis Commander: http://localhost:8081")
            print("  2. Backup your agents.json file before deleting:")
            print("     cp server_python/data/agents.json server_python/data/agents.json.backup")
            print("  3. Once verified, you can safely delete:")
            print("     - server_python/data/agents.json")
            print("     - server_python/utils/agent_storage.py")

    except Exception as e:
        print(f"\n❌ Migration failed with error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Disconnect
        print("\n[Cleanup] Disconnecting from Redis...")
        await redis_service.disconnect()
        print("✅ Disconnected")


if __name__ == "__main__":
    print("\n⚠️  Before running migration:")
    print("  1. Make sure Redis is running: docker-compose up -d")
    print("  2. Backup your data: cp server_python/data/agents.json agents.json.backup")
    print("\nStarting migration in 3 seconds...")
    print("Press Ctrl+C to cancel\n")

    try:
        import time
        time.sleep(3)
        asyncio.run(migrate())
    except KeyboardInterrupt:
        print("\n\n❌ Migration cancelled by user")
