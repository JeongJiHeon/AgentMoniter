"""
Schema Inferrer Unit Tests

LLM 기반 TaskSchema 추론기의 단위 테스트입니다.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from agents.schema_inferrer import SchemaInferrer, InferenceResult


class TestSchemaInferrerKeywordFallback:
    """키워드 기반 Fallback 추론 테스트"""

    @pytest.fixture
    def inferrer(self):
        """SchemaInferrer 인스턴스 (fallback 활성화)"""
        return SchemaInferrer(fallback_to_keyword=True)

    def test_lunch_keywords(self, inferrer):
        """점심/음식 관련 키워드 감지"""
        test_cases = [
            "오늘 점심 뭐 먹을까?",
            "강남 맛집 추천해줘",
            "저녁 메뉴 추천",
            "근처 식당 찾아줘",
            "밥 먹을 곳 알려줘",
        ]

        for request in test_cases:
            result = inferrer._infer_with_keywords(request)
            assert result.task_type == "lunch_booking", f"Failed for: {request}"
            assert result.confidence == 0.7

    def test_booking_keywords(self, inferrer):
        """예약 관련 키워드 감지"""
        # 음식 관련 키워드가 없는 순수 예약 케이스만 테스트
        test_cases = [
            "회의실 예약해줘",
            "내일 3시 booking 부탁",
            "미팅룸 잡아줘",
        ]

        for request in test_cases:
            result = inferrer._infer_with_keywords(request)
            assert result.task_type == "booking", f"Failed for: {request}"
            assert result.confidence == 0.7

    def test_general_fallback(self, inferrer):
        """특정 패턴 미감지 시 general로 분류"""
        test_cases = [
            "오늘 날씨 어때?",
            "코드 리뷰해줘",
            "문서 정리해줘",
        ]

        for request in test_cases:
            result = inferrer._infer_with_keywords(request)
            assert result.task_type == "general", f"Failed for: {request}"
            assert result.confidence == 0.5


class TestSchemaInferrerLLM:
    """LLM 기반 추론 테스트"""

    @pytest.fixture
    def inferrer(self):
        """SchemaInferrer 인스턴스"""
        return SchemaInferrer(fallback_to_keyword=True)

    @pytest.mark.asyncio
    async def test_infer_with_llm_success(self, inferrer):
        """LLM 추론 성공 케이스"""
        mock_response = json.dumps({
            "task_type": "lunch_booking",
            "confidence": 0.95,
            "reasoning": "음식 및 장소 관련 요청",
            "extracted_entities": {
                "location": "강남역",
                "party_size": 4
            }
        })

        with patch("agents.schema_inferrer.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            result = await inferrer._infer_with_llm("강남역에서 4명 점심 추천해줘")

            assert result.task_type == "lunch_booking"
            assert result.confidence == 0.95
            assert result.extracted_entities["location"] == "강남역"
            assert result.extracted_entities["party_size"] == 4

    @pytest.mark.asyncio
    async def test_infer_with_llm_json_code_block(self, inferrer):
        """LLM 응답이 코드 블록으로 감싸진 경우"""
        mock_response = """
        ```json
        {
            "task_type": "booking",
            "confidence": 0.85,
            "reasoning": "예약 관련 요청",
            "extracted_entities": {"time": "15:00"}
        }
        ```
        """

        with patch("agents.schema_inferrer.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            result = await inferrer._infer_with_llm("오후 3시 회의실 예약해줘")

            assert result.task_type == "booking"
            assert result.confidence == 0.85

    @pytest.mark.asyncio
    async def test_infer_with_llm_fallback_on_error(self, inferrer):
        """LLM 실패 시 키워드 fallback"""
        with patch("agents.schema_inferrer.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = Exception("LLM API Error")

            result = await inferrer.infer("점심 추천해줘")

            # 키워드 fallback이 동작해야 함
            assert result.task_type == "lunch_booking"
            assert result.confidence == 0.7

    @pytest.mark.asyncio
    async def test_infer_with_llm_invalid_json(self, inferrer):
        """LLM이 잘못된 JSON 반환 시"""
        with patch("agents.schema_inferrer.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "This is not valid JSON"

            result = await inferrer.infer("예약해줘")

            # 키워드 fallback
            assert result.task_type == "booking"


class TestSchemaInferrerCache:
    """캐시 동작 테스트"""

    @pytest.fixture
    def inferrer(self):
        """SchemaInferrer 인스턴스"""
        return SchemaInferrer(fallback_to_keyword=True)

    @pytest.mark.asyncio
    async def test_cache_hit(self, inferrer):
        """캐시 히트 테스트"""
        mock_response = json.dumps({
            "task_type": "lunch_booking",
            "confidence": 0.9,
            "reasoning": "테스트",
            "extracted_entities": {}
        })

        with patch("agents.schema_inferrer.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            # 첫 번째 호출
            result1 = await inferrer.infer("점심 추천")

            # 두 번째 호출 (캐시 히트)
            result2 = await inferrer.infer("점심 추천")

            # LLM은 한 번만 호출되어야 함
            assert mock_llm.call_count == 1

            # 결과는 동일해야 함
            assert result1.task_type == result2.task_type

    @pytest.mark.asyncio
    async def test_cache_case_insensitive(self, inferrer):
        """캐시 키 대소문자 무시"""
        mock_response = json.dumps({
            "task_type": "general",
            "confidence": 0.8,
            "reasoning": "테스트",
            "extracted_entities": {}
        })

        with patch("agents.schema_inferrer.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            await inferrer.infer("TEST REQUEST")
            await inferrer.infer("test request")

            # 대소문자가 다르지만 같은 캐시 키로 처리
            assert mock_llm.call_count == 1

    def test_clear_cache(self, inferrer):
        """캐시 초기화"""
        # 캐시에 수동으로 데이터 추가
        inferrer._cache["test_key"] = InferenceResult(
            task_type="test",
            confidence=0.5,
            reasoning="test",
            extracted_entities={}
        )

        assert len(inferrer._cache) == 1

        inferrer.clear_cache()

        assert len(inferrer._cache) == 0


class TestSchemaInferrerIntegration:
    """통합 테스트"""

    @pytest.fixture
    def inferrer(self):
        """SchemaInferrer 인스턴스"""
        return SchemaInferrer(fallback_to_keyword=True)

    @pytest.mark.asyncio
    async def test_infer_and_get_schema(self, inferrer):
        """추론 및 스키마 조회"""
        mock_response = json.dumps({
            "task_type": "lunch_booking",
            "confidence": 0.9,
            "reasoning": "점심 예약 요청",
            "extracted_entities": {"location": "강남"}
        })

        with patch("agents.schema_inferrer.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            schema, result = await inferrer.infer_and_get_schema("강남에서 점심 예약해줘")

            assert result.task_type == "lunch_booking"
            assert schema is not None or result.task_type == "general"  # 스키마가 등록되어 있는 경우

    @pytest.mark.asyncio
    async def test_infer_unknown_schema_falls_to_general(self, inferrer):
        """알 수 없는 스키마 타입은 general로 fallback"""
        mock_response = json.dumps({
            "task_type": "unknown_type_xyz",
            "confidence": 0.7,
            "reasoning": "알 수 없는 타입",
            "extracted_entities": {}
        })

        with patch("agents.schema_inferrer.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            schema, result = await inferrer.infer_and_get_schema("알 수 없는 요청")

            # 등록되지 않은 스키마는 general로 fallback
            assert result.task_type == "general" or result.confidence == 0.3

    def test_get_schema_returns_none_for_unknown(self, inferrer):
        """등록되지 않은 스키마 타입 조회"""
        schema = inferrer.get_schema("nonexistent_schema_type")
        assert schema is None


class TestInferenceResult:
    """InferenceResult 데이터 클래스 테스트"""

    def test_inference_result_creation(self):
        """InferenceResult 생성"""
        result = InferenceResult(
            task_type="lunch_booking",
            confidence=0.85,
            reasoning="음식 관련 키워드 감지",
            extracted_entities={"location": "강남", "party_size": 3}
        )

        assert result.task_type == "lunch_booking"
        assert result.confidence == 0.85
        assert result.reasoning == "음식 관련 키워드 감지"
        assert result.extracted_entities["location"] == "강남"
        assert result.extracted_entities["party_size"] == 3

    def test_inference_result_defaults(self):
        """InferenceResult 기본값"""
        result = InferenceResult(
            task_type="general",
            confidence=0.5,
            reasoning="",
            extracted_entities={}
        )

        assert result.extracted_entities == {}
        assert result.reasoning == ""
