"""
TaskHandlers - Task 상호작용 관련 핸들러

처리하는 메시지 타입:
- TASK_INTERACTION_CLIENT
"""

from .base_handler import BaseHandler


class TaskHandlers(BaseHandler):
    """Task 상호작용 메시지 핸들러"""

    async def handle_task_interaction(self, client_id: str, payload: dict):
        """Task 상호작용 메시지 처리 (TASK_INTERACTION_CLIENT)"""
        task_id = payload.get('taskId')
        user_message = payload.get('message')
        role = payload.get('role', 'user')

        self.log(f"Processing task_interaction: taskId={task_id}, role={role}, message={user_message[:50]}...")

        # Dynamic Orchestration에서 대기 중인 워크플로우 확인
        if await self._handle_dynamic_workflow(task_id, user_message):
            return

        # 기존 workflow_manager 확인 (하위 호환성)
        if await self._handle_legacy_workflow(task_id, user_message):
            return

        # 일반 메시지 처리 (워크플로우 없음)
        await self._handle_general_message(task_id, user_message)

    async def _handle_dynamic_workflow(self, task_id: str, user_message: str) -> bool:
        """Dynamic Orchestration 워크플로우 처리"""
        if not self.dynamic_orchestration:
            return False

        if not self.dynamic_orchestration.has_pending_workflow(task_id):
            return False

        self.log(f"Found pending dynamic workflow for task {task_id}, resuming...")

        # Dynamic Orchestration 초기화
        self.dynamic_orchestration.set_ws_server(self.ws_server)

        # 사용자 입력으로 워크플로우 재개
        result = await self.dynamic_orchestration.resume_with_user_input(task_id, user_message)

        if result is None:
            # 또 다른 사용자 입력 대기 중
            self.log(f"Workflow paused again for user input: {task_id}")
            return True

        # 워크플로우 완료
        workflow = self.dynamic_orchestration.get_workflow(task_id)
        if workflow:
            self.broadcast_agent_log(
                agent_id="orchestrator-system",
                agent_name="Orchestration Agent",
                log_type="info",
                message="🎉 워크플로우 완료",
                details=f"사용자 입력: {user_message}",
                task_id=task_id
            )

        # 완료된 워크플로우 정리
        self.dynamic_orchestration.remove_workflow(task_id)

        self.log(f"Dynamic workflow completed for task {task_id}")
        return True

    async def _handle_legacy_workflow(self, task_id: str, user_message: str) -> bool:
        """기존 Workflow Manager 처리 (하위 호환성)"""
        if not self.workflow_manager:
            return False

        if not await self.workflow_manager.has_pending_workflow(task_id):
            return False

        self.log(f"Found pending workflow for task {task_id}, resuming...")

        # Orchestration Engine 초기화
        if self.orchestration_engine:
            self.orchestration_engine.set_ws_server(self.ws_server)

            # resume_workflow로 중앙 실행 루프 재개
            result = await self.orchestration_engine.resume_workflow(task_id, user_message)

            if result is None:
                self.log(f"Workflow paused again for user input: {task_id}")
                return True

            # 워크플로우 완료
            workflow = await self.workflow_manager.get_workflow(task_id)
            if workflow:
                self.broadcast_agent_log(
                    agent_id=workflow.steps[-1].agent_id if workflow.steps else "system",
                    agent_name=workflow.steps[-1].agent_name if workflow.steps else "System",
                    log_type="info",
                    message="🎉 워크플로우 완료",
                    details=f"사용자 입력: {user_message}",
                    task_id=task_id
                )

            # 완료된 워크플로우 정리
            await self.workflow_manager.remove_workflow(task_id)

            self.log(f"Workflow completed for task {task_id}")
            return True

        return False

    async def _handle_general_message(self, task_id: str, user_message: str):
        """일반 메시지 처리 (워크플로우 없음)"""
        # Orchestration Agent 찾기
        orchestration_agent = self.find_orchestration_agent()

        if not orchestration_agent:
            self.log("ERROR: No agents available")
            self.broadcast_task_interaction(
                task_id=task_id,
                role='system',
                message="사용 가능한 Agent가 없습니다. 먼저 Agent를 생성해주세요.",
                agent_id=None,
                agent_name="System"
            )
            return

        self.log(f"Using Orchestration Agent: {orchestration_agent.name} ({orchestration_agent.id})")

        # Agent 로그: Task 처리 시작
        self.broadcast_agent_log(
            agent_id=orchestration_agent.id,
            agent_name=orchestration_agent.name,
            log_type='info',
            message=f"Task 처리 시작: {user_message[:50]}...",
            details=f"Task ID: {task_id}\n전체 메시지: {user_message}",
            task_id=task_id
        )

        try:
            # Planning 시작 로그
            self.broadcast_agent_log(
                agent_id=orchestration_agent.id,
                agent_name=orchestration_agent.name,
                log_type='info',
                message="🔍 Planning: 요청 분석 및 실행 계획 수립 중...",
                details=f"요청: {user_message}",
                task_id=task_id
            )

            # 프론트엔드에 Agent 선택 요청
            available_agents = self.get_available_agents_info(
                exclude_agent_id=orchestration_agent.id
            )

            self.broadcast_message({
                'type': 'request_agent_selection',
                'payload': {
                    'task_id': task_id,
                    'user_message': user_message,
                    'available_agents': available_agents
                }
            })

            # 실행 계획 (프론트엔드에서 재호출 시 처리)
            execution_plan = []

            if execution_plan:
                await self._execute_plan(
                    task_id, user_message, orchestration_agent, execution_plan
                )
            else:
                self.broadcast_agent_log(
                    agent_id=orchestration_agent.id,
                    agent_name=orchestration_agent.name,
                    log_type='info',
                    message="일반 질문으로 판단",
                    details="Specialist Agent 없이 Answer Agent가 직접 답변합니다.",
                    task_id=task_id
                )

            # 최종 답변 생성
            await self._generate_final_answer(
                task_id, user_message, orchestration_agent, execution_plan, []
            )

        except Exception as e:
            self.log(f"ERROR processing task_interaction: {e}")
            import traceback
            traceback.print_exc()

            self.broadcast_task_interaction(
                task_id=task_id,
                role='system',
                message=f"메시지 처리 중 오류가 발생했습니다: {str(e)}",
                agent_id=None,
                agent_name="System"
            )

    async def _execute_plan(
        self,
        task_id: str,
        user_message: str,
        orchestration_agent,
        execution_plan: list
    ) -> list:
        """실행 계획 순차 실행"""
        from agents.orchestration import call_llm

        agent_results = []

        # 실행 계획 로그
        plan_details = "\n".join([
            f"  Step {i+1}: {item['agent'].name} ({item['description']})"
            for i, item in enumerate(execution_plan)
        ])
        self.broadcast_agent_log(
            agent_id=orchestration_agent.id,
            agent_name=orchestration_agent.name,
            log_type='decision',
            message=f"📋 실행 계획 수립 완료 ({len(execution_plan)}개 Agent)",
            details=f"실행 순서:\n{plan_details}",
            task_id=task_id
        )

        # 순차 실행
        for step_num, plan_item in enumerate(execution_plan, 1):
            specialist = plan_item['agent']
            task_desc = plan_item['description']

            # 작업 시작 로그
            self.broadcast_agent_log(
                agent_id=specialist.id,
                agent_name=specialist.name,
                log_type='info',
                message=f"🔧 작업 시작: {task_desc}",
                details=f"Step {step_num}/{len(execution_plan)}",
                task_id=task_id
            )

            # LLM 호출로 Agent 작업 수행
            prev_results_text = ""
            if agent_results:
                prev_results_text = "\n\n이전 작업 결과:\n" + "\n".join([
                    f"- {r['agent']}: {r['result']}" for r in agent_results
                ])

            agent_messages = [
                {
                    "role": "system",
                    "content": f"당신은 '{specialist.name}'입니다. {specialist.description if hasattr(specialist, 'description') else ''}\n주어진 작업을 수행하고 결과를 간결하게 요약해주세요."
                },
                {
                    "role": "user",
                    "content": f"""다음 작업을 수행해주세요:

**사용자 요청**: {user_message}
**담당 작업**: {task_desc}
{prev_results_text}

작업을 수행하고 결과를 간결하게 응답해주세요."""
                }
            ]

            llm_result = await call_llm(agent_messages, max_tokens=500)

            # 결과 저장
            if llm_result and 'error' not in llm_result.lower():
                result_text = llm_result
            else:
                result_text = f"{task_desc} 작업이 수행되었습니다."

            result = {
                'agent': specialist.name,
                'task': task_desc,
                'result': result_text
            }
            agent_results.append(result)

            # 작업 완료 로그
            result_preview = result['result'][:80] + "..." if len(result['result']) > 80 else result['result']
            self.broadcast_agent_log(
                agent_id=specialist.id,
                agent_name=specialist.name,
                log_type='info',
                message="✅ 작업 완료",
                details=result_preview,
                task_id=task_id
            )

            self.log(f"Step {step_num} completed: {specialist.name}")

        return agent_results

    async def _generate_final_answer(
        self,
        task_id: str,
        user_message: str,
        orchestration_agent,
        execution_plan: list,
        agent_results: list
    ):
        """최종 답변 생성"""
        from agents.orchestration import call_llm

        self.broadcast_agent_log(
            agent_id="answer-agent-system",
            agent_name="Answer Agent",
            log_type='info',
            message="📝 최종 답변 생성 중...",
            details=f"종합할 결과: {len(agent_results)}개",
            task_id=task_id
        )

        # LLM으로 최종 답변 생성
        results_text = ""
        if agent_results:
            for i, res in enumerate(agent_results, 1):
                results_text += f"Step {i}. {res['agent']}: {res['result']}\n"

        llm_final_messages = [
            {
                "role": "system",
                "content": "당신은 친절한 AI 어시스턴트입니다. 작업 결과를 사용자에게 알기 쉽게 요약해서 전달해주세요. 이모지를 적절히 사용하고, 마크다운 형식으로 응답하세요."
            },
            {
                "role": "user",
                "content": f"""다음 사용자 요청과 처리 결과를 바탕으로 친절한 응답을 작성해주세요:

**사용자 요청**: {user_message}

**처리 결과**:
{results_text if results_text else "처리된 결과가 없습니다."}

사용자에게 유용하고 친절한 응답을 작성해주세요."""
            }
        ]

        final_answer = await call_llm(llm_final_messages, max_tokens=1000)

        if not final_answer or ("LLM" in final_answer and "오류" in final_answer):
            if agent_results:
                final_answer = f"'{user_message}'에 대한 처리가 완료되었습니다. 추가로 도움이 필요하시면 말씀해주세요."
            else:
                final_answer = "메시지를 확인했습니다. 어떻게 도와드릴까요?"

        # 응답 Agent 결정
        display_agent = execution_plan[-1]['agent'] if execution_plan else orchestration_agent

        # 최종 응답 브로드캐스트
        self.broadcast_task_interaction(
            task_id=task_id,
            role='agent',
            message=final_answer,
            agent_id=display_agent.id,
            agent_name=display_agent.name
        )
        self.log(f"Final response broadcasted for task {task_id}")

        # 답변 완료 로그
        self.broadcast_agent_log(
            agent_id="answer-agent-system",
            agent_name="Answer Agent",
            log_type='info',
            message="✅ 답변 완료",
            details="사용자에게 최종 답변을 전달했습니다.",
            task_id=task_id
        )

        # Orchestration 완료 로그
        agent_names = " → ".join([item['agent'].name for item in execution_plan]) if execution_plan else "Direct"
        self.broadcast_agent_log(
            agent_id=orchestration_agent.id,
            agent_name=orchestration_agent.name,
            log_type='info',
            message="🎉 Task 완료",
            details=f"실행 흐름: Orchestration → {agent_names} → Answer Agent",
            task_id=task_id
        )
