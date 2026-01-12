#!/usr/bin/env python3
"""
Production-grade Orchestration 모듈
멀티-에이전트 워크플로우 관리, 실행 루프, LLM 호출 최적화
"""
import asyncio
import aiohttp
import os
import json
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from contextlib import asynccontextmanager

# =============================================================================
# LLM Client (Connection Pooling, Retry, Timeout)
# =============================================================================

class LLMClient:
    """
    LLM API 클라이언트 - Connection pooling, retry, timeout 지원
    Singleton 패턴으로 전역 재사용
    """
    _instance: Optional['LLMClient'] = None
    _session: Optional[aiohttp.ClientSession] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        self._initialized = getattr(self, '_initialized', False)
        if self._initialized:
            return  # Singleton: 이미 초기화됨
        
        self.api_url = os.getenv("LLM_API_URL", "https://api.platform.a15t.com/v1/chat/completions")
        self.api_key = os.getenv("LLM_API_KEY", "")
        self.model = os.getenv("LLM_MODEL", "azure/openai/gpt-4o")
        self.default_temperature = float(os.getenv("LLM_TEMPERATURE", "1.0"))
        self.max_tokens = int(os.getenv("LLM_MAX_TOKENS", "8000"))
        self.timeout = aiohttp.ClientTimeout(total=120, connect=10)  # timeout 증가
        self.max_retries = 3
        self.retry_delay = 1.0
        self._initialized = True
        
        # 환경 변수 로드 상태 출력
        self._print_config()
    
    def _print_config(self):
        """현재 설정 출력"""
        api_key_status = "✅ 설정됨" if self.api_key else "❌ 미설정"
        print(f"[LLMClient] API URL: {self.api_url}")
        print(f"[LLMClient] API Key: {api_key_status}")
        print(f"[LLMClient] Model: {self.model}")
        print(f"[LLMClient] Temperature: {self.default_temperature}")
        print(f"[LLMClient] Max Tokens: {self.max_tokens}")
    
    def update_config(self, provider: str = None, model: str = None, api_key: str = None, 
                     base_url: str = None, temperature: float = None, max_tokens: int = None):
        """
        프론트엔드에서 전달받은 LLM 설정으로 업데이트
        """
        updated = []
        
        if base_url is not None and base_url.strip():
            # base_url에 /chat/completions가 없으면 추가
            base_url = base_url.strip()
            if not base_url.endswith('/chat/completions'):
                if base_url.endswith('/'):
                    base_url = base_url + 'chat/completions'
                elif base_url.endswith('/v1'):
                    base_url = base_url + '/chat/completions'
                elif '/v1' in base_url:
                    base_url = base_url.rstrip('/') + '/chat/completions'
                else:
                    base_url = base_url.rstrip('/') + '/v1/chat/completions'
            
            if base_url != self.api_url:
                self.api_url = base_url
                updated.append(f"api_url={base_url}")
        
        if api_key is not None and api_key != self.api_key:
            self.api_key = api_key
            updated.append("api_key=***")
        
        if model is not None and model != self.model:
            # model이 이미 provider/model 형식이면 그대로 사용
            # 예: "azure/openai/gpt-5-2025-08-07-gs" -> 그대로
            # 예: "gpt-4o" + provider="openai" -> "openai/gpt-4o" (필요시)
            # 하지만 프론트엔드에서 이미 조합된 형식으로 올 가능성이 높으므로 그대로 사용
            if '/' in model:
                # 이미 provider/model 형식
                self.model = model
            elif provider:
                # provider와 model 분리된 경우 조합
                self.model = f"{provider}/{model}"
            else:
                # model만 있는 경우 그대로 사용
                self.model = model
            updated.append(f"model={self.model}")
        
        if temperature is not None and temperature != self.default_temperature:
            self.default_temperature = temperature
            updated.append(f"temperature={temperature}")
        
        if max_tokens is not None and max_tokens != self.max_tokens:
            self.max_tokens = max_tokens
            updated.append(f"max_tokens={max_tokens}")
        
        if updated:
            print(f"[LLMClient] 설정 업데이트: {', '.join(updated)}")
            self._print_config()
        
        return len(updated) > 0
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """세션 재사용 (Connection pooling)"""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(limit=20, limit_per_host=10)
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=self.timeout
            )
        return self._session
    
    async def close(self):
        """세션 종료"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    def _is_fixed_temperature_model(self) -> bool:
        """temperature=1만 지원하는 모델인지 확인"""
        model_lower = self.model.lower()
        # o1, o3 reasoning 모델 및 일부 특수 모델은 temperature=1만 지원
        fixed_temp_patterns = [
            'o1', 'o3', 'o1-', 'o3-', '/o1', '/o3',
            'gpt-5', 'gpt5',  # GPT-5 계열
        ]
        return any(pattern in model_lower for pattern in fixed_temp_patterns)

    async def call(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = None,  # None이면 기본값 사용
        json_mode: bool = False
    ) -> str:
        """
        LLM API 호출 with retry & timeout
        """
        if not self.api_key:
            print("[LLM] Warning: LLM_API_KEY not set")
            return '{"error": "LLM API 키가 설정되지 않았습니다."}'

        # temperature가 None이면 기본값 사용
        actual_temperature = temperature if temperature is not None else self.default_temperature

        # 일부 모델은 temperature=1만 지원
        if self._is_fixed_temperature_model() and actual_temperature != 1.0:
            print(f"[LLM] Fixed-temperature model detected ({self.model}), forcing temperature=1.0")
            actual_temperature = 1.0
        
        session = await self._get_session()
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_completion_tokens": max_tokens,
            "temperature": actual_temperature,
            "stream": False
        }
        
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        
        last_error = None
        print(f"[LLM] Calling API: {self.api_url}, model={self.model}, messages={len(messages)}")
        for attempt in range(self.max_retries):
            try:
                async with session.post(
                    self.api_url,
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"[LLM] Raw API response: {json.dumps(data, ensure_ascii=False)[:500]}...")
                        
                        # Azure OpenAI / OpenAI 형식
                        content = ""
                        if "choices" in data and data["choices"]:
                            choice = data["choices"][0]
                            if "message" in choice:
                                content = choice["message"].get("content", "")
                            elif "text" in choice:
                                content = choice["text"]
                        
                        # Anthropic 형식 대응
                        if not content and "content" in data:
                            if isinstance(data["content"], list):
                                for item in data["content"]:
                                    if item.get("type") == "text":
                                        content = item.get("text", "")
                                        break
                            elif isinstance(data["content"], str):
                                content = data["content"]
                        
                        print(f"[LLM] Parsed content: {len(content)} chars, preview: {content[:100] if content else 'EMPTY'}...")
                        return content
                    elif response.status == 429:  # Rate limit
                        retry_after = float(response.headers.get("Retry-After", self.retry_delay * (attempt + 1)))
                        print(f"[LLM] Rate limited, waiting {retry_after}s...")
                        await asyncio.sleep(retry_after)
                        continue
                    else:
                        error_text = await response.text()
                        last_error = f"API Error ({response.status}): {error_text}"
                        print(f"[LLM] {last_error}")
                        
            except asyncio.TimeoutError:
                last_error = "Timeout"
                print(f"[LLM] Timeout on attempt {attempt + 1}")
            except Exception as e:
                last_error = str(e)
                print(f"[LLM] Error on attempt {attempt + 1}: {e}")
            
            if attempt < self.max_retries - 1:
                await asyncio.sleep(self.retry_delay * (attempt + 1))
        
        return json.dumps({"error": last_error or "Unknown error"})


# 전역 LLM 클라이언트
llm_client = LLMClient()


async def call_llm(
    messages: List[Dict[str, str]],
    max_tokens: int = 1000,
    temperature: float = None,  # None이면 환경 변수 기본값 사용
    json_mode: bool = False
) -> str:
    """LLM 호출 유틸리티 함수 (하위 호환성)"""
    return await llm_client.call(messages, max_tokens, temperature, json_mode)


# =============================================================================
# Step Status Enum
# =============================================================================

class StepStatus(str, Enum):
    """워크플로우 스텝 상태"""
    PENDING = "pending"           # 대기 중
    RUNNING = "running"           # 실행 중
    WAITING_USER = "waiting_user" # 사용자 입력 대기
    COMPLETED = "completed"       # 완료
    FAILED = "failed"             # 실패


# =============================================================================
# Agent Context & Result (Agent 간 데이터 전달)
# =============================================================================

@dataclass
class AgentContext:
    """Agent 실행 컨텍스트"""
    task_id: str
    task_content: str
    step_description: str
    previous_results: List[Dict[str, Any]] = field(default_factory=list)
    user_inputs: Dict[str, str] = field(default_factory=dict)  # step_id -> input
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Agent 실행 결과 (Structured)"""
    success: bool
    output: str
    data: Optional[Dict[str, Any]] = None  # Structured data
    needs_user_input: bool = False
    user_prompt: str = ""
    error: Optional[str] = None


# =============================================================================
# Base Agent (Abstract)
# =============================================================================

class BaseAgent(ABC):
    """
    Agent 추상 클래스
    - 각 Agent는 고유한 실행 전략, Tool, Prompt를 가짐
    """
    
    def __init__(self, agent_id: str, name: str, description: str = ""):
        self.id = agent_id
        self.name = name
        self.description = description
        self.system_prompt: str = ""
        self.tools: List[str] = []
    
    @abstractmethod
    async def run(self, context: AgentContext) -> AgentResult:
        """
        Agent 실행 - 반드시 구현해야 함
        """
        pass
    
    def get_system_prompt(self) -> str:
        """시스템 프롬프트 반환"""
        return self.system_prompt or f"당신은 '{self.name}' Agent입니다. {self.description}"


class LLMAgent(BaseAgent):
    """
    LLM 기반 Agent - 기본 구현
    """
    
    def __init__(
        self,
        agent_id: str,
        name: str,
        description: str = "",
        system_prompt: str = "",
        output_schema: Optional[Dict[str, Any]] = None
    ):
        super().__init__(agent_id, name, description)
        self.system_prompt = system_prompt
        self.output_schema = output_schema  # JSON Schema for structured output
    
    async def run(self, context: AgentContext) -> AgentResult:
        """LLM을 통한 Agent 실행"""
        try:
            # 이전 결과를 컨텍스트로 포함
            prev_results_text = ""
            if context.previous_results:
                prev_results_text = "\n\n**이전 작업 결과:**\n" + "\n".join([
                    f"- {r.get('agent', 'Agent')}: {r.get('result', '')}"
                    for r in context.previous_results
                ])
            
            # 사용자 입력 포함
            user_inputs_text = ""
            if context.user_inputs:
                user_inputs_text = "\n\n**사용자 입력:**\n" + "\n".join([
                    f"- {k}: {v}" for k, v in context.user_inputs.items()
                ])
            
            messages = [
                {
                    "role": "system",
                    "content": self.get_system_prompt()
                },
                {
                    "role": "user",
                    "content": f"""다음 작업을 수행해주세요:

**요청**: {context.task_content}
**담당 작업**: {context.step_description}
{prev_results_text}
{user_inputs_text}

작업을 수행하고 결과를 JSON 형식으로 응답해주세요:
{{"output": "작업 결과", "data": {{"key": "value"}}}}"""
                }
            ]
            
            print(f"[LLMAgent] {self.name}: Calling LLM...")
            response = await call_llm(messages, max_tokens=4000, json_mode=True)
            print(f"[LLMAgent] {self.name}: Response = {response[:200] if response else 'EMPTY'}...")
            
            # JSON 파싱 시도
            try:
                result_data = json.loads(response)
                output = result_data.get("output", response)
                print(f"[LLMAgent] {self.name}: Parsed output = {output[:100] if output else 'EMPTY'}...")
                return AgentResult(
                    success=True,
                    output=output,
                    data=result_data.get("data")
                )
            except json.JSONDecodeError:
                # JSON 파싱 실패 시 raw output 반환
                print(f"[LLMAgent] {self.name}: JSON parse failed, using raw response")
                return AgentResult(
                    success=True,
                    output=response
                )
                
        except Exception as e:
            return AgentResult(
                success=False,
                output="",
                error=str(e)
            )


# =============================================================================
# Workflow Step & State
# =============================================================================

@dataclass
class WorkflowStep:
    """워크플로우의 각 단계"""
    id: str  # 고유 ID
    agent_id: str
    agent_name: str
    description: str
    order: int
    needs_user_input: bool = False
    input_prompt: str = ""
    status: StepStatus = StepStatus.PENDING
    result: Optional[AgentResult] = None
    user_input: Optional[str] = None  # 이 스텝에 대한 사용자 입력
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class WorkflowState:
    """진행 중인 워크플로우 상태"""
    task_id: str
    task_content: str
    steps: List[WorkflowStep]
    current_step_index: int = 0
    status: str = "running"  # running, waiting_user, completed, failed
    created_at: datetime = field(default_factory=datetime.now)
    
    def get_current_step(self) -> Optional[WorkflowStep]:
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None
    
    def is_completed(self) -> bool:
        return self.current_step_index >= len(self.steps)
    
    def advance(self) -> None:
        """다음 스텝으로 이동"""
        if not self.is_completed():
            self.current_step_index += 1
    
    def get_results(self) -> List[Dict[str, Any]]:
        """완료된 스텝들의 결과 반환"""
        return [
            {
                "agent": step.agent_name,
                "result": step.result.output if step.result else "",
                "data": step.result.data if step.result else None
            }
            for step in self.steps
            if step.status == StepStatus.COMPLETED and step.result
        ]
    
    def get_user_inputs(self) -> Dict[str, str]:
        """스텝별 사용자 입력 반환"""
        return {
            step.id: step.user_input
            for step in self.steps
            if step.user_input is not None
        }


# =============================================================================
# Workflow Manager (Thread-safe)
# =============================================================================

class WorkflowManager:
    """워크플로우 상태 관리자 - 동시성 안전"""
    
    def __init__(self):
        self._workflows: Dict[str, WorkflowState] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()
    
    async def _get_lock(self, task_id: str) -> asyncio.Lock:
        """task_id별 Lock 획득"""
        async with self._global_lock:
            if task_id not in self._locks:
                self._locks[task_id] = asyncio.Lock()
            return self._locks[task_id]
    
    async def create_workflow(
        self,
        task_id: str,
        task_content: str,
        steps: List[WorkflowStep]
    ) -> WorkflowState:
        """새 워크플로우 생성"""
        lock = await self._get_lock(task_id)
        async with lock:
            workflow = WorkflowState(
                task_id=task_id,
                task_content=task_content,
                steps=steps
            )
            self._workflows[task_id] = workflow
            return workflow
    
    async def get_workflow(self, task_id: str) -> Optional[WorkflowState]:
        """워크플로우 조회"""
        lock = await self._get_lock(task_id)
        async with lock:
            return self._workflows.get(task_id)
    
    async def has_pending_workflow(self, task_id: str) -> bool:
        """대기 중인 워크플로우가 있는지 확인"""
        lock = await self._get_lock(task_id)
        async with lock:
            workflow = self._workflows.get(task_id)
            return workflow is not None and workflow.status == "waiting_user"
    
    async def remove_workflow(self, task_id: str) -> Optional[WorkflowState]:
        """워크플로우 제거"""
        lock = await self._get_lock(task_id)
        async with lock:
            workflow = self._workflows.pop(task_id, None)
            # Lock도 정리
            async with self._global_lock:
                self._locks.pop(task_id, None)
            return workflow
    
    async def update_step_status(
        self,
        task_id: str,
        step_index: int,
        status: StepStatus,
        result: Optional[AgentResult] = None
    ) -> None:
        """스텝 상태 업데이트"""
        lock = await self._get_lock(task_id)
        async with lock:
            workflow = self._workflows.get(task_id)
            if workflow and 0 <= step_index < len(workflow.steps):
                step = workflow.steps[step_index]
                step.status = status
                if result:
                    step.result = result
                if status == StepStatus.RUNNING:
                    step.started_at = datetime.now()
                elif status in (StepStatus.COMPLETED, StepStatus.FAILED):
                    step.completed_at = datetime.now()
    
    async def add_user_input(self, task_id: str, user_input: str) -> None:
        """현재 스텝에 사용자 입력 추가"""
        lock = await self._get_lock(task_id)
        async with lock:
            workflow = self._workflows.get(task_id)
            if workflow:
                current_step = workflow.get_current_step()
                if current_step:
                    current_step.user_input = user_input
                    current_step.status = StepStatus.COMPLETED
                workflow.status = "running"
    
    async def set_workflow_status(self, task_id: str, status: str) -> None:
        """워크플로우 상태 설정"""
        lock = await self._get_lock(task_id)
        async with lock:
            workflow = self._workflows.get(task_id)
            if workflow:
                workflow.status = status


# =============================================================================
# Agent Registry
# =============================================================================

class AgentRegistry:
    """
    Agent 레지스트리 - Agent 인스턴스 관리
    """
    
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
    
    def register(self, agent: BaseAgent) -> None:
        """Agent 등록"""
        self._agents[agent.id] = agent
    
    def get(self, agent_id: str) -> Optional[BaseAgent]:
        """Agent 조회"""
        return self._agents.get(agent_id)
    
    def get_or_create_llm_agent(
        self,
        agent_id: str,
        name: str,
        description: str = ""
    ) -> BaseAgent:
        """Agent 조회 또는 LLMAgent 생성"""
        if agent_id not in self._agents:
            self._agents[agent_id] = LLMAgent(
                agent_id=agent_id,
                name=name,
                description=description
            )
        return self._agents[agent_id]


# =============================================================================
# Orchestration Engine (Central Execution Loop)
# =============================================================================

class OrchestrationEngine:
    """
    멀티-에이전트 오케스트레이션 엔진
    중앙 실행 루프 + Agent 실행 + 상태 관리
    """
    
    def __init__(self, workflow_manager: WorkflowManager):
        self.workflow_manager = workflow_manager
        self.agent_registry = AgentRegistry()
        self.ws_server: Any = None
    
    def set_ws_server(self, ws_server: Any) -> None:
        """WebSocket 서버 설정"""
        self.ws_server = ws_server
    
    async def run_workflow(self, task_id: str) -> Optional[str]:
        """
        중앙 실행 루프 - 워크플로우 전체 실행
        Returns: 최종 응답 또는 None (사용자 입력 대기)
        """
        workflow = await self.workflow_manager.get_workflow(task_id)
        if not workflow:
            return None
        
        while not workflow.is_completed():
            step = workflow.get_current_step()
            if not step:
                break
            
            # 스텝 실행
            await self.workflow_manager.update_step_status(
                task_id, workflow.current_step_index, StepStatus.RUNNING
            )
            
            self._log(
                agent_id=step.agent_id,
                agent_name=step.agent_name,
                log_type="info",
                message=f"🔧 작업 시작: {step.description}",
                details=f"Step {step.order}/{len(workflow.steps)}",
                task_id=task_id
            )
            
            # Agent 실행
            agent = self.agent_registry.get_or_create_llm_agent(
                step.agent_id, step.agent_name, step.description
            )
            
            context = AgentContext(
                task_id=task_id,
                task_content=workflow.task_content,
                step_description=step.description,
                previous_results=workflow.get_results(),
                user_inputs=workflow.get_user_inputs()
            )
            
            result = await agent.run(context)
            
            if result.success:
                await self.workflow_manager.update_step_status(
                    task_id, workflow.current_step_index, StepStatus.COMPLETED, result
                )
                
                self._log(
                    agent_id=step.agent_id,
                    agent_name=step.agent_name,
                    log_type="info",
                    message=f"✅ 작업 완료",
                    details=result.output[:100] + "..." if len(result.output) > 100 else result.output,
                    task_id=task_id
                )
            else:
                await self.workflow_manager.update_step_status(
                    task_id, workflow.current_step_index, StepStatus.FAILED, result
                )
                
                self._log(
                    agent_id=step.agent_id,
                    agent_name=step.agent_name,
                    log_type="error",
                    message=f"❌ 작업 실패",
                    details=result.error or "Unknown error",
                    task_id=task_id
                )
            
            # 사용자 입력이 필요한 경우: 일시 중지
            if step.needs_user_input and step.input_prompt:
                await self.workflow_manager.update_step_status(
                    task_id, workflow.current_step_index, StepStatus.WAITING_USER
                )
                await self.workflow_manager.set_workflow_status(task_id, "waiting_user")
                
                self._log(
                    agent_id="question-agent-system",
                    agent_name="Question Agent",
                    log_type="info",
                    message="❓ 사용자 입력 요청",
                    details=step.input_prompt,
                    task_id=task_id
                )
                
                # 사용자에게 질문 표시
                if self.ws_server:
                    self.ws_server.broadcast_task_interaction(
                        task_id=task_id,
                        role='agent',
                        message=step.input_prompt,
                        agent_id=step.agent_id,
                        agent_name=step.agent_name
                    )
                
                return None  # 사용자 입력 대기
            
            # 다음 스텝으로
            workflow.advance()
        
        # 모든 스텝 완료: 최종 응답 생성
        return await self.generate_final_response(workflow, task_id)
    
    async def resume_workflow(self, task_id: str, user_input: str) -> Optional[str]:
        """
        워크플로우 재개 - 사용자 입력 후
        """
        await self.workflow_manager.add_user_input(task_id, user_input)
        
        workflow = await self.workflow_manager.get_workflow(task_id)
        if workflow:
            current_step = workflow.get_current_step()
            if current_step:
                self._log(
                    agent_id=current_step.agent_id,
                    agent_name=current_step.agent_name,
                    log_type="info",
                    message=f"✅ 사용자 입력 수신: {user_input}",
                    details="워크플로우 재개",
                    task_id=task_id
                )
            
            # 다음 스텝으로 진행
            workflow.advance()
        
        return await self.run_workflow(task_id)
    
    async def generate_final_response(
        self,
        workflow: WorkflowState,
        task_id: str
    ) -> str:
        """Answer Agent를 통한 최종 응답 생성"""
        self._log(
            agent_id="answer-agent-system",
            agent_name="Answer Agent",
            log_type="info",
            message="📝 최종 응답 생성 중...",
            details=f"처리된 결과: {len(workflow.get_results())}개",
            task_id=task_id
        )
        
        results = workflow.get_results()
        results_text = "\n".join([
            f"- {r['agent']}: {r['result']}"
            for r in results
        ])
        
        user_inputs = workflow.get_user_inputs()
        user_inputs_text = ""
        if user_inputs:
            user_inputs_text = "\n\n사용자 입력:\n" + "\n".join([
                f"- {v}" for v in user_inputs.values()
            ])
        
        messages = [
            {
                "role": "system",
                "content": "당신은 친절한 AI 어시스턴트입니다. 작업 결과를 사용자에게 알기 쉽게 요약해서 전달해주세요. 이모지를 적절히 사용하고, 마크다운 형식으로 응답하세요."
            },
            {
                "role": "user",
                "content": f"""다음 정보를 바탕으로 사용자에게 유용한 응답을 작성해주세요:

**원래 요청**: {workflow.task_content}

**처리 결과**:
{results_text}
{user_inputs_text}

친절하고 도움이 되는 방식으로 응답해주세요."""
            }
        ]
        
        final_response = await call_llm(messages, max_tokens=4000)
        
        if not final_response or "error" in final_response.lower():
            final_response = f"✅ 작업이 완료되었습니다.\n\n📋 처리 내역:\n{results_text}"
        
        # 마지막 Agent 이름으로 응답
        last_step = workflow.steps[-1] if workflow.steps else None
        display_id = last_step.agent_id if last_step else "answer-agent-system"
        display_name = last_step.agent_name if last_step else "Answer Agent"
        
        if self.ws_server:
            self.ws_server.broadcast_task_interaction(
                task_id=task_id,
                role='agent',
                message=final_response,
                agent_id=display_id,
                agent_name=display_name
            )
        
        self._log(
            agent_id="answer-agent-system",
            agent_name="Answer Agent",
            log_type="info",
            message="✅ 최종 응답 완료",
            details="사용자에게 응답 전송됨",
            task_id=task_id
        )
        
        # 워크플로우 완료
        await self.workflow_manager.set_workflow_status(task_id, "completed")
        
        return final_response
    
    def _log(
        self,
        agent_id: str,
        agent_name: str,
        log_type: str,
        message: str,
        details: str = "",
        task_id: str = None
    ) -> None:
        """Agent Activity 로그"""
        if self.ws_server:
            self.ws_server.broadcast_agent_log(
                agent_id=agent_id,
                agent_name=agent_name,
                log_type=log_type,
                message=message,
                details=details,
                task_id=task_id
            )


# =============================================================================
# Utility Functions
# =============================================================================

def build_workflow_steps(
    planned_agents: List[Dict[str, Any]],
    agent_map: Dict[str, Any]
) -> List[WorkflowStep]:
    """
    프론트엔드 계획 → WorkflowStep 리스트 변환
    """
    from uuid import uuid4
    
    steps = []
    for i, planned in enumerate(planned_agents):
        agent_id = planned.get('agentId')
        if agent_id in agent_map:
            agent = agent_map[agent_id]
            step = WorkflowStep(
                id=str(uuid4()),  # 고유 ID
                agent_id=agent_id,
                agent_name=agent.name,
                description=planned.get('reason', planned.get('agentName', '')),
                order=planned.get('order', i + 1),
                needs_user_input=planned.get('needsUserInput', False),
                input_prompt=planned.get('inputPrompt', '')
            )
            steps.append(step)
    
    steps.sort(key=lambda s: s.order)
    return steps


# =============================================================================
# Global Instances
# =============================================================================

workflow_manager = WorkflowManager()
orchestration_engine = OrchestrationEngine(workflow_manager)
