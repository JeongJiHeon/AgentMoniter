"""
AgentHandlers - Agent 관련 핸들러

처리하는 메시지 타입:
- ASSIGN_TASK
- CREATE_AGENT
"""

import asyncio
from typing import Callable, Awaitable

from .base_handler import BaseHandler


class AgentHandlers(BaseHandler):
    """Agent 관련 메시지 핸들러"""

    def __init__(
        self,
        ws_server,
        agent_registry,
        dynamic_orchestration=None,
        orchestration_engine=None,
        workflow_manager=None,
        process_agent_task: Callable = None
    ):
        """
        AgentHandlers 초기화

        Args:
            process_agent_task: Agent Task 처리 함수 (비동기)
        """
        super().__init__(
            ws_server,
            agent_registry,
            dynamic_orchestration,
            orchestration_engine,
            workflow_manager
        )
        self._process_agent_task = process_agent_task

    async def handle_assign_task(self, client_id: str, payload: dict):
        """Task를 Agent에게 할당 (ASSIGN_TASK)"""
        task_id = payload.get('taskId')
        agent_id = payload.get('agentId')
        task_data = payload.get('task', {})

        # 멀티-에이전트 플랜
        orchestration_plan = payload.get('orchestrationPlan', {})
        planned_agents = orchestration_plan.get('agents', [])
        needs_user_input = orchestration_plan.get('needsUserInput', False)
        input_prompt = orchestration_plan.get('inputPrompt', '')

        self.log(f"Assigning task {task_id} to agent {agent_id}")
        if planned_agents:
            self.log(f"Multi-agent plan: {[a.get('agentName') for a in planned_agents]}")

        # Agent 조회 - 실제 등록된 Agent만 사용
        agent = self.get_agent(agent_id)
        if not agent:
            self.log(f"Agent {agent_id} not found in registry, auto-creating...")

            # planned_agents에서 해당 Agent 정보 찾기
            agent_info = None
            for pa in planned_agents:
                if pa.get('agentId') == agent_id:
                    agent_info = pa
                    break

            if agent_info:
                agent = await self._auto_create_agent(
                    agent_id,
                    agent_info,
                    task_data
                )
            else:
                self.log(f"ERROR: Agent {agent_id} not found in planned_agents either")
                self.broadcast_notification(
                    f"Agent {agent_id} not found. Please create the agent first.",
                    "error"
                )
                return

        self.log(f"Found/Created agent: {agent.name} ({agent.id})")

        # Agent 초기화 및 시작
        await self._initialize_agent_if_needed(agent, agent_id)

        # Agent에게 Task 할당 및 처리 시작
        try:
            from agents.types import AgentInput
            agent_input = AgentInput(
                type='task',
                content=task_data.get('description', task_data.get('title', '')),
                metadata={
                    'task_id': task_id,
                    'title': task_data.get('title'),
                    'priority': task_data.get('priority'),
                    'source': task_data.get('source'),
                    'tags': task_data.get('tags', []),
                    'orchestration_plan': orchestration_plan,
                    'planned_agents': planned_agents,
                    'needs_user_input': needs_user_input,
                    'input_prompt': input_prompt,
                }
            )

            # 비동기로 Agent 처리 시작
            if self._process_agent_task:
                asyncio.create_task(self._process_agent_task(agent, agent_input))
            self.log(f"Started agent task processing for task {task_id}")

        except Exception as e:
            self.log(f"Error starting agent task: {e}")
            import traceback
            traceback.print_exc()

    async def handle_create_agent(self, client_id: str, payload: dict):
        """Agent 생성 요청 처리 (CREATE_AGENT)"""
        self.log(f"Received CREATE_AGENT message from {client_id}")
        self.log(f"Message payload: {payload}")

        try:
            agent_id = payload.get('id')
            agent_name = payload.get('name')
            agent_type = payload.get('type', 'custom')
            description = payload.get('description', '')
            constraints = payload.get('constraints', [])
            permissions = payload.get('permissions', {})
            custom_config = payload.get('customConfig', {})

            if not agent_id or not agent_name:
                self.log("ERROR: Missing required fields (id, name)")
                self.broadcast_notification(
                    "Agent creation failed: Missing required fields",
                    "error"
                )
                return

            # 이미 존재하는 Agent인지 확인
            existing_agent = self.get_agent(agent_id)
            if existing_agent:
                self.log(f"Agent {agent_id} already exists, skipping creation")
                return

            # Agent 생성
            from agents.types import AgentConfig
            from agents import TaskProcessorAgent

            config = AgentConfig(
                name=agent_name,
                type=agent_type,
                description=description,
                constraints=constraints,
                permissions=permissions,
                custom_config=custom_config
            )

            agent = TaskProcessorAgent(config, agent_id, ws_server=self.ws_server)

            # Agent 등록
            self.register_agent(agent)

            # Agent 초기화 및 시작
            await self._initialize_agent_if_needed(agent, agent_id)

            # 저장
            await self._save_agent_config(agent_id, agent_name, agent_type, description, constraints, custom_config)

            # Agent 상태 브로드캐스트
            state = agent.get_state()
            self.broadcast_agent_update(state)

            self.broadcast_notification(
                f"Agent '{agent_name}' has been created successfully!",
                "success"
            )

            self.log(f"Agent {agent_name} ({agent_id}) created and registered")

        except Exception as e:
            self.log(f"Error creating agent: {e}")
            import traceback
            traceback.print_exc()
            self.broadcast_notification(
                f"Failed to create agent: {str(e)}",
                "error"
            )

    async def _auto_create_agent(self, agent_id: str, agent_info: dict, task_data: dict):
        """Agent 자동 생성"""
        agent_name = agent_info.get('agentName', f'Agent-{agent_id[:8]}')
        self.log(f"Auto-creating agent: {agent_name} ({agent_id})")

        from agents.generic_agent import GenericAgent
        from agents.types import AgentConfig

        config = AgentConfig(
            name=agent_name,
            type='custom',
            description=f'Auto-created agent for task: {task_data.get("title", "Unknown")}',
            constraints=[],
            capabilities=['general'],
        )

        agent = GenericAgent(config)
        agent._id = agent_id
        agent._state.id = agent_id
        self.register_agent(agent)

        # WebSocket으로 Agent 업데이트 브로드캐스트
        self.broadcast_agent_update(agent.get_state())

        self.log(f"Agent {agent_name} auto-created and registered")
        return agent

    async def _initialize_agent_if_needed(self, agent, agent_id: str):
        """Agent 초기화 (필요한 경우)"""
        if not hasattr(agent, 'context') or (hasattr(agent, 'context') and agent.context is None):
            self.log(f"Initializing agent {agent_id}")
            from agents.types import AgentExecutionContext
            from models.ontology import OntologyContext

            ontology_context = OntologyContext(
                activePreferences=[],
                activeTaboos=[],
                activeApprovalRules=[],
                matchedFailurePatterns=[],
                appliedConstraints=[]
            )

            context = AgentExecutionContext(
                agent_id=agent_id,
                ontology_context=ontology_context,
                current_ticket=None,
                previous_decisions=[]
            )

            try:
                if hasattr(agent, 'initialize'):
                    await agent.initialize(context)
                if hasattr(agent, 'start'):
                    await agent.start()
                self.log(f"Agent {agent_id} initialized and started")
            except Exception as e:
                self.log(f"Error initializing agent: {e}")
                import traceback
                traceback.print_exc()
                raise

    async def _save_agent_config(
        self,
        agent_id: str,
        agent_name: str,
        agent_type: str,
        description: str,
        constraints: list,
        custom_config: dict
    ):
        """Agent 설정 저장"""
        try:
            from utils.agent_storage import save_agent

            agent_data = {
                "id": agent_id,
                "name": agent_name,
                "type": agent_type,
                "description": description,
                "constraints": constraints,
                "customConfig": custom_config
            }
            save_agent(agent_data)
            self.log(f"Agent config saved: {agent_name}")
        except Exception as e:
            self.log(f"Error saving agent config: {e}")
