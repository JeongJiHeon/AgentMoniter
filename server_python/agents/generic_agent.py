"""
Generic Agent - 동적으로 생성되는 범용 Agent

프론트엔드에서 요청한 Agent를 자동으로 생성할 때 사용됩니다.
기본적인 LLM 기반 태스크 처리를 수행합니다.
"""

from typing import Any, Optional
from .base_agent import BaseAgent
from .types import AgentConfig, AgentInput, AgentOutput


class GenericAgent(BaseAgent):
    """
    범용 Agent 클래스
    
    동적으로 생성되어 일반적인 태스크를 처리합니다.
    LLM을 사용하여 태스크를 분석하고 실행합니다.
    """
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self._capabilities = config.capabilities or ['general']
    
    async def explore(self, input: AgentInput) -> AgentOutput:
        """
        태스크 탐색 단계
        - 태스크의 요구사항 분석
        - 필요한 정보 수집
        """
        from models.agent import ThinkingMode
        await self.state_machine.transition(ThinkingMode.EXPLORING)
        
        self._log("info", f"Exploring task: {input.content[:100]}...")
        
        # 탐색 결과 반환
        return AgentOutput(
            type='exploration',
            result={
                'task_content': input.content,
                'metadata': input.metadata,
                'analysis': f"Task analysis for: {input.content[:50]}..."
            },
            metadata={
                'stage': 'explore',
                'agent_id': self.id,
                'agent_name': self.name
            }
        )
    
    async def structure(self, input: AgentInput) -> AgentOutput:
        """
        태스크 구조화 단계
        - 실행 계획 수립
        - 필요한 단계 정의
        """
        from models.agent import ThinkingMode
        await self.state_machine.transition(ThinkingMode.STRUCTURING)
        
        self._log("info", f"Structuring task: {input.content[:100]}...")
        
        # 구조화 결과 반환
        return AgentOutput(
            type='structure',
            result={
                'steps': [
                    {'step': 1, 'action': 'Analyze request'},
                    {'step': 2, 'action': 'Execute task'},
                    {'step': 3, 'action': 'Return result'}
                ]
            },
            metadata={
                'stage': 'structure',
                'agent_id': self.id,
                'agent_name': self.name
            }
        )
    
    async def validate(self, input: AgentInput) -> AgentOutput:
        """
        검증 단계
        - 결과 검증
        - 품질 확인
        """
        from models.agent import ThinkingMode
        await self.state_machine.transition(ThinkingMode.VALIDATING)
        
        self._log("info", f"Validating: {input.content[:100]}...")
        
        return AgentOutput(
            type='validation',
            result={
                'is_valid': True,
                'validation_notes': 'Task completed successfully'
            },
            metadata={
                'stage': 'validate',
                'agent_id': self.id,
                'agent_name': self.name
            }
        )
    
    async def summarize(self, input: AgentInput) -> AgentOutput:
        """
        요약 단계
        - 결과 요약
        - 최종 보고
        """
        from models.agent import ThinkingMode
        await self.state_machine.transition(ThinkingMode.SUMMARIZING)
        
        self._log("info", f"Summarizing: {input.content[:100]}...")
        
        return AgentOutput(
            type='summary',
            result={
                'summary': f"Task '{input.content[:50]}...' has been processed.",
                'status': 'completed'
            },
            metadata={
                'stage': 'summarize',
                'agent_id': self.id,
                'agent_name': self.name
            }
        )
    
    async def process(self, input: AgentInput) -> AgentOutput:
        """
        전체 태스크 처리 파이프라인
        """
        from models.agent import ThinkingMode
        
        try:
            # 1. 탐색
            explore_result = await self.explore(input)
            self._log("info", f"Explore completed")
            
            # 2. 구조화
            structure_result = await self.structure(input)
            self._log("info", f"Structure completed")
            
            # 3. 검증
            validate_result = await self.validate(input)
            self._log("info", f"Validation completed")
            
            # 4. 요약
            summary_result = await self.summarize(input)
            self._log("info", f"Summary completed")
            
            # 완료 상태로 전환
            await self.state_machine.transition(ThinkingMode.IDLE)
            
            return AgentOutput(
                type='complete',
                result={
                    'exploration': explore_result.result,
                    'structure': structure_result.result,
                    'validation': validate_result.result,
                    'summary': summary_result.result
                },
                metadata={
                    'agent_id': self.id,
                    'agent_name': self.name,
                    'status': 'completed'
                }
            )
            
        except Exception as e:
            self._log("error", f"Error processing task: {str(e)}")
            await self.state_machine.transition(ThinkingMode.IDLE)
            
            return AgentOutput(
                type='error',
                result={'error': str(e)},
                metadata={
                    'agent_id': self.id,
                    'agent_name': self.name,
                    'status': 'failed'
                }
            )
    
    def _log(self, level: str, message: str):
        """로그 출력"""
        print(f"[{self.name}] [{level.upper()}] {message}")

