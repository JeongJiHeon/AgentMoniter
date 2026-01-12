"""
MCPInitializer - MCP 서비스 초기화

MCP 서비스 및 MCP Agent 등록을 담당합니다.
"""

import os
from typing import Optional


class MCPInitializer:
    """MCP 서비스 초기화 클래스"""

    def __init__(self, mcp_registry, agent_registry):
        """
        MCPInitializer 초기화

        Args:
            mcp_registry: MCP 서비스 레지스트리
            agent_registry: Agent 레지스트리
        """
        self.mcp_registry = mcp_registry
        self.agent_registry = agent_registry

    async def initialize_all(self) -> dict:
        """
        모든 MCP 서비스 초기화

        Returns:
            초기화 결과 상태
        """
        result = {
            "services": [],
            "agents": [],
            "errors": []
        }

        # MCP 서비스 등록
        print("\n[MCPInitializer] Registering MCP Services...")
        try:
            await self._register_services()
            status = self.mcp_registry.get_status()
            result["services"] = status
            print(f"  - Registered: {status['total']} services")
        except Exception as e:
            result["errors"].append(f"Service registration error: {e}")
            print(f"  - Error registering services: {e}")

        # MCP Agent 등록
        print("\n[MCPInitializer] Registering MCP Background Agents...")

        # Notion MCP Agent
        notion_result = await self._register_notion_agent()
        if notion_result:
            result["agents"].append(notion_result)

        # Slack MCP Agent
        slack_result = await self._register_slack_agent()
        if slack_result:
            result["agents"].append(slack_result)

        return result

    async def _register_services(self):
        """MCP 서비스 등록"""
        from mcp import NotionService, GmailService, SlackService
        from mcp.types import MCPServiceConfig

        # Notion 서비스
        notion_service = NotionService(MCPServiceConfig(
            type="notion",
            name="Notion Workspace",
            enabled=True,
            credentials={"apiKey": os.getenv("NOTION_API_KEY", "demo-key")}
        ))

        # Gmail 서비스
        gmail_service = GmailService(MCPServiceConfig(
            type="gmail",
            name="Gmail Account",
            enabled=True
        ))

        # Slack 서비스
        slack_service = SlackService(MCPServiceConfig(
            type="slack",
            name="Slack Workspace",
            enabled=True,
            credentials={
                "accessToken": os.getenv("SLACK_BOT_TOKEN", ""),
                "webhookUrl": os.getenv("SLACK_WEBHOOK_URL", "")
            }
        ))

        # 레지스트리에 등록
        self.mcp_registry.register(notion_service, MCPServiceConfig(
            type="notion",
            name="Notion Workspace",
            enabled=True
        ))

        self.mcp_registry.register(gmail_service, MCPServiceConfig(
            type="gmail",
            name="Gmail Account",
            enabled=True
        ))

        self.mcp_registry.register(slack_service, MCPServiceConfig(
            type="slack",
            name="Slack Workspace",
            enabled=True
        ))

    async def _register_notion_agent(self) -> Optional[dict]:
        """Notion MCP Agent 등록"""
        try:
            from agents.notion_mcp_agent import notion_mcp_agent
            from agents.types import AgentExecutionContext
            from models.ontology import OntologyContext

            notion_api_key = os.getenv("NOTION_API_KEY", "demo-key")
            if notion_api_key and notion_api_key != "demo-key":
                notion_mcp_agent.configure(notion_api_key)
                await notion_mcp_agent.connect()

            self.agent_registry.register_agent(notion_mcp_agent)

            # Agent 초기화 및 시작
            ontology_context = OntologyContext(
                activePreferences=[],
                activeTaboos=[],
                activeApprovalRules=[],
                matchedFailurePatterns=[],
                appliedConstraints=[]
            )

            context = AgentExecutionContext(
                agent_id=notion_mcp_agent.id,
                ontology_context=ontology_context,
                current_ticket=None,
                previous_decisions=[]
            )

            await notion_mcp_agent.initialize(context)
            await notion_mcp_agent.start()

            print(f"  - Registered: {notion_mcp_agent.name} ({notion_mcp_agent.id})")
            return {"name": notion_mcp_agent.name, "id": notion_mcp_agent.id}

        except Exception as e:
            print(f"  - Failed to register Notion MCP Agent: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def _register_slack_agent(self) -> Optional[dict]:
        """Slack MCP Agent 등록"""
        try:
            from agents.slack_mcp_agent import slack_mcp_agent
            from agents.types import AgentExecutionContext
            from models.ontology import OntologyContext

            slack_bot_token = os.getenv("SLACK_BOT_TOKEN", "")
            slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")

            if slack_bot_token or slack_webhook_url:
                slack_mcp_agent.configure(
                    bot_token=slack_bot_token if slack_bot_token else None,
                    webhook_url=slack_webhook_url if slack_webhook_url else None
                )
                await slack_mcp_agent.connect()

            self.agent_registry.register_agent(slack_mcp_agent)

            # Agent 초기화 및 시작
            ontology_context = OntologyContext(
                activePreferences=[],
                activeTaboos=[],
                activeApprovalRules=[],
                matchedFailurePatterns=[],
                appliedConstraints=[]
            )

            context = AgentExecutionContext(
                agent_id=slack_mcp_agent.id,
                ontology_context=ontology_context,
                current_ticket=None,
                previous_decisions=[]
            )

            await slack_mcp_agent.initialize(context)
            await slack_mcp_agent.start()

            print(f"  - Registered: {slack_mcp_agent.name} ({slack_mcp_agent.id})")
            return {"name": slack_mcp_agent.name, "id": slack_mcp_agent.id}

        except Exception as e:
            print(f"  - Failed to register Slack MCP Agent: {e}")
            import traceback
            traceback.print_exc()
            return None


async def initialize_mcp_services(mcp_registry, agent_registry) -> dict:
    """
    MCP 서비스 초기화 (헬퍼 함수)

    Args:
        mcp_registry: MCP 서비스 레지스트리
        agent_registry: Agent 레지스트리

    Returns:
        초기화 결과
    """
    initializer = MCPInitializer(mcp_registry, agent_registry)
    return await initializer.initialize_all()
