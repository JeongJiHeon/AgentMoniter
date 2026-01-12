#!/usr/bin/env python3
"""
Schema Inferrer - LLM 기반 TaskSchema 추론

키워드 기반 매칭 대신 LLM을 사용하여 더 정확한 Task 유형을 추론합니다.
"""

import json
import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from models.orchestration import call_llm
from .task_schema import TaskSchema, TaskSchemaRegistry


@dataclass
class InferenceResult:
    """추론 결과"""
    task_type: str
    confidence: float
    reasoning: str
    extracted_entities: Dict[str, Any]


class SchemaInferrer:
    """
    LLM 기반 Schema 추론기

    책임:
    - 사용자 요청 분석
    - 적절한 TaskSchema 추론
    - 엔티티 추출
    """

    def __init__(self, fallback_to_keyword: bool = True):
        """
        Args:
            fallback_to_keyword: LLM 실패 시 키워드 기반 fallback 사용
        """
        self._fallback_to_keyword = fallback_to_keyword
        self._cache: Dict[str, InferenceResult] = {}

    async def infer(self, user_request: str) -> InferenceResult:
        """
        사용자 요청에서 TaskSchema 추론

        Args:
            user_request: 사용자 요청 텍스트

        Returns:
            InferenceResult
        """
        # 캐시 확인
        cache_key = user_request.strip().lower()[:100]
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            result = await self._infer_with_llm(user_request)
            self._cache[cache_key] = result
            return result
        except Exception as e:
            print(f"[SchemaInferrer] LLM inference failed: {e}")

            if self._fallback_to_keyword:
                return self._infer_with_keywords(user_request)

            raise

    async def _infer_with_llm(self, user_request: str) -> InferenceResult:
        """LLM을 통한 추론"""
        # 사용 가능한 스키마 목록
        available_schemas = TaskSchemaRegistry.get_all()
        schema_descriptions = []

        for task_type, schema in available_schemas.items():
            schema_descriptions.append(
                f"- {task_type}: required_facts={schema.required_facts}, "
                f"required_decisions={schema.required_decisions}"
            )

        schemas_text = "\n".join(schema_descriptions)

        messages = [
            {
                "role": "system",
                "content": """당신은 사용자 요청을 분석하여 적절한 Task 유형을 판단하는 분석가입니다.

주어진 Task Schema 목록에서 가장 적합한 것을 선택하세요.

JSON 형식으로 응답하세요:
```json
{
  "task_type": "선택한 task_type",
  "confidence": 0.0~1.0,
  "reasoning": "선택 이유",
  "extracted_entities": {
    "location": "추출된 위치 (있으면)",
    "datetime": "추출된 일시 (있으면)",
    "party_size": "추출된 인원 (있으면)",
    ...
  }
}
```

규칙:
1. 명확하지 않으면 "general"을 선택
2. 음식/식당/메뉴 관련은 "lunch_booking"
3. 예약/booking 관련은 "booking"
4. extracted_entities에는 요청에서 추출 가능한 정보만 포함"""
            },
            {
                "role": "user",
                "content": f"""사용 가능한 Task Schema:
{schemas_text}

사용자 요청:
"{user_request}"

위 요청에 가장 적합한 Task Schema를 선택하고, 추출 가능한 엔티티를 반환하세요."""
            }
        ]

        response = await call_llm(messages, max_tokens=1000, json_mode=True)

        # JSON 파싱
        try:
            # 코드 블록 추출
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
            if json_match:
                response = json_match.group(1).strip()

            data = json.loads(response)

            return InferenceResult(
                task_type=data.get("task_type", "general"),
                confidence=float(data.get("confidence", 0.5)),
                reasoning=data.get("reasoning", ""),
                extracted_entities=data.get("extracted_entities", {})
            )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"[SchemaInferrer] JSON parse error: {e}")
            raise

    def _infer_with_keywords(self, user_request: str) -> InferenceResult:
        """키워드 기반 추론 (Fallback)"""
        request_lower = user_request.lower()

        # 점심/저녁/메뉴/식당 관련 키워드
        lunch_keywords = ["점심", "저녁", "메뉴", "추천", "식당", "맛집", "밥", "음식"]
        if any(kw in request_lower for kw in lunch_keywords):
            return InferenceResult(
                task_type="lunch_booking",
                confidence=0.7,
                reasoning="키워드 기반 매칭: 음식 관련 키워드 감지",
                extracted_entities={}
            )

        # 예약 관련 키워드
        booking_keywords = ["예약", "booking", "reserve", "잡아", "신청"]
        if any(kw in request_lower for kw in booking_keywords):
            return InferenceResult(
                task_type="booking",
                confidence=0.7,
                reasoning="키워드 기반 매칭: 예약 관련 키워드 감지",
                extracted_entities={}
            )

        # 기본값
        return InferenceResult(
            task_type="general",
            confidence=0.5,
            reasoning="키워드 기반 매칭: 특정 패턴 미감지",
            extracted_entities={}
        )

    def get_schema(self, task_type: str) -> Optional[TaskSchema]:
        """task_type으로 Schema 조회"""
        return TaskSchemaRegistry.get(task_type)

    async def infer_and_get_schema(self, user_request: str) -> tuple[TaskSchema, InferenceResult]:
        """
        추론 및 Schema 반환

        Returns:
            (TaskSchema, InferenceResult) 튜플
        """
        result = await self.infer(user_request)
        schema = self.get_schema(result.task_type)

        if schema is None:
            # Fallback to general
            schema = TaskSchemaRegistry.get("general")
            result.task_type = "general"
            result.confidence = 0.3

        return schema, result

    def clear_cache(self) -> None:
        """캐시 초기화"""
        self._cache.clear()


# 전역 인스턴스
schema_inferrer = SchemaInferrer()
