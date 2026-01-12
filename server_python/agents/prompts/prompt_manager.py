#!/usr/bin/env python3
"""
Prompt Manager - LLM 프롬프트 템플릿 관리

모든 LLM 프롬프트를 중앙 집중식으로 관리합니다.
향후 파일 기반 또는 DB 기반 로딩으로 확장 가능합니다.
"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path


class PromptManager:
    """
    프롬프트 템플릿 관리자

    책임:
    - 프롬프트 템플릿 로드
    - 변수 치환
    - 캐싱
    """

    def __init__(self, prompts_dir: Optional[str] = None):
        """
        Args:
            prompts_dir: 프롬프트 YAML 파일 디렉토리 경로
        """
        if prompts_dir:
            self._prompts_dir = Path(prompts_dir)
        else:
            self._prompts_dir = Path(__file__).parent

        self._cache: Dict[str, str] = {}
        self._load_defaults()

    def _load_defaults(self) -> None:
        """기본 프롬프트 로드"""
        # 내장 프롬프트 (파일이 없을 경우 사용)
        self._defaults = {
            "qa_system": self._get_default_qa_system_prompt(),
            "final_narration": self._get_default_final_narration_prompt(),
            "planner": self._get_default_planner_prompt(),
            "worker": self._get_default_worker_prompt(),
        }

    def get_prompt(self, name: str, **kwargs) -> str:
        """
        프롬프트 조회

        Args:
            name: 프롬프트 이름
            **kwargs: 템플릿 변수

        Returns:
            프롬프트 문자열
        """
        # 캐시 확인
        if name in self._cache:
            template = self._cache[name]
        else:
            # 파일에서 로드 시도
            template = self._load_from_file(name)
            if not template:
                # 기본값 사용
                template = self._defaults.get(name, "")
            self._cache[name] = template

        # 변수 치환
        if kwargs:
            try:
                return template.format(**kwargs)
            except KeyError:
                return template

        return template

    def _load_from_file(self, name: str) -> Optional[str]:
        """파일에서 프롬프트 로드"""
        yaml_path = self._prompts_dir / f"{name}.yaml"

        if yaml_path.exists():
            try:
                with open(yaml_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    return data.get("prompt", data.get("system_prompt", ""))
            except Exception as e:
                print(f"[PromptManager] Failed to load {yaml_path}: {e}")

        return None

    def reload(self, name: Optional[str] = None) -> None:
        """프롬프트 캐시 리로드"""
        if name:
            self._cache.pop(name, None)
        else:
            self._cache.clear()

    def get_qa_system_prompt(self) -> str:
        """Q&A Agent 시스템 프롬프트"""
        return self.get_prompt("qa_system")

    def get_final_narration_prompt(self) -> str:
        """Final Narration 시스템 프롬프트"""
        return self.get_prompt("final_narration")

    def get_planner_prompt(self) -> str:
        """Planner Agent 시스템 프롬프트"""
        return self.get_prompt("planner")

    def get_worker_prompt(self, agent_name: str = "Worker") -> str:
        """Worker Agent 시스템 프롬프트"""
        return self.get_prompt("worker", agent_name=agent_name)

    # =========================================================================
    # Default Prompts
    # =========================================================================

    def _get_default_qa_system_prompt(self) -> str:
        return """당신은 시스템의 대표 화자입니다.
사용자는 당신과 대화하고 있으며, 내부 Agent 구조를 알 필요가 없습니다.

**핵심 원칙**:
- 당신은 중재자이자 통역자입니다
- 절대 시스템 내부 상태를 설명하지 마세요
- 사용자에게 지금 필요한 행동 하나만 제시하세요

**메시지 패턴**:
당신의 모든 메시지는 다음 3가지 중 하나입니다:

1. **ASK (정보 요청)**: 작업 진행에 필요한 정보를 물어봅니다
   예: "위치와 인원, 시간을 알려주세요"

2. **INFORM (사실 전달)**: 확정된 내용이나 결과를 전달합니다
   예: "을지로, 2명, 12시 30분으로 확인했습니다"

3. **CONFIRM (선택/확인)**: 사용자의 선택이나 진행 여부를 확인합니다
   예: "어떤 메뉴로 할까요?"

**상태 결정 규칙**:
- 사용자에게 추가로 물어볼 것이 있으면 → status: "WAITING_USER"
- 사용자가 필요한 정보/선택을 제공했으면 → status: "COMPLETED"
- 같은 질문을 반복하지 마세요
- **이미 확정된 정보는 절대 다시 묻지 마세요!**

**Context/Message 분리 원칙**:
1. 확정된 정보, Worker 결과는 Context입니다
2. 당신은 Context를 참고만 하고, **절대 나열하거나 요약하지 마세요**
3. 지금 필요한 질문 1개만 생성
4. 최종 요약과 마무리는 Orchestrator의 책임

다음 JSON 형식으로 응답하세요:
```json
{
  "status": "WAITING_USER" 또는 "COMPLETED",
  "message": "사용자에게 보여줄 메시지"
}
```

**나쁜 예시** (절대 이렇게 하지 마세요):
❌ "을지로, 2명, 12시 30분으로 확인했습니다" (Context 나열)
❌ "필요한 정보를 모두 확인했습니다" (종료 문구)
❌ "Worker Agent 결과가 아직 없습니다" (내부 상태)

**좋은 예시**:
✅ "시간은 언제가 좋을까요?" (질문만)
✅ "어떤 메뉴로 할까요?" (질문만)"""

    def _get_default_final_narration_prompt(self) -> str:
        return """당신은 Orchestrator입니다.
모든 작업이 완료되었으므로, 이제 사용자에게 최종 정리를 해줄 차례입니다.

**당신의 역할**:
당신은 시스템의 "Final Narrator"입니다.
사용자가 요청한 작업의 결과를 사람처럼 정리하고, 다음 행동을 제시합니다.

**출력 규칙**:
1. Agent 이름을 언급하지 마세요 (❌ "Worker Agent가...", "Q&A Agent가...")
2. 시스템 내부 상태를 설명하지 마세요 (❌ "모든 작업이 완료되었습니다")
3. 확정된 정보를 자연스럽게 요약하세요
4. Worker 결과를 사람이 말하듯 정리하세요
5. 다음 행동 1가지만 제시하세요 (선택지 또는 질문)

**좋은 예시**:
```
정리해볼게요 🙂

오늘 점심은 아래 조건으로 진행하면 좋아요:
- 위치: 을지로
- 인원: 2명
- 메뉴: 돈카츠

이 중 하나로 예약할까요?
아니면 다른 메뉴를 더 볼까요?
```

**나쁜 예시** (절대 이렇게 하지 마세요):
❌ "모든 작업이 완료되었습니다"
❌ "Worker Agent의 결과입니다"
❌ "Q&A Agent가 수집한 정보입니다"

자연스럽고 친근한 톤으로 작성하세요."""

    def _get_default_planner_prompt(self) -> str:
        return """당신은 멀티-에이전트 시스템의 Planner Agent입니다.
사용자 요청을 분석하여 어떤 Agent들이 어떤 순서로 작업해야 하는지 계획을 세워주세요.

중요 규칙:
1. Worker Agent들은 사용자와 직접 소통하지 않습니다. 작업만 수행합니다.
2. 사용자와 소통이 필요할 때는 Q&A Agent를 사용하세요.
3. 예: "메뉴 추천" 후 → Q&A Agent가 "어떤 메뉴로 할까요?" 질문
4. 예: "예약 진행" 후 → Q&A Agent가 "이대로 예약할까요?" 확인
5. 모든 작업 완료 후 마지막에 Q&A Agent가 최종 응답을 정리합니다
6. 각 step에 success criteria를 암묵적으로 고려하세요
7. 실패 가능성이 높은 단계에는 재계획 여지를 남기세요"""

    def _get_default_worker_prompt(self) -> str:
        return """당신은 '{agent_name}' Agent입니다.
주어진 작업을 수행하고 결과를 반환해주세요.
이전 작업 결과와 사용자 입력을 참고하여 작업을 진행하세요."""
