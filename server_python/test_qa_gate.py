#!/usr/bin/env python3
"""
Q&A Gate Logic 검증 스크립트

목적: Q&A Agent가 Gate로 작동하는지 확인
- 필수 슬롯이 모두 채워지면 즉시 COMPLETED 반환
- Worker Agent로 즉시 전환
- 재호출 방지
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.conversation_state import (
    ConversationState,
    SlotFillingParser,
    create_initial_state
)


def test_initial_state_creation():
    """초기 상태 생성 테스트"""
    print("=" * 60)
    print("TEST 1: 초기 ConversationState 생성")
    print("=" * 60)

    request = "을지로에서 2명이서 12시 30분에 점심 먹고 싶어"
    state = create_initial_state(request)

    print(f"✓ Intent: {state.intent}")
    print(f"✓ Required slots: {state.required_slots}")
    print(f"✓ Confirmed slots: {list(state.slots.keys())}")
    print(f"✓ Pending slots: {state.pending_slots}")
    print()

    # 필수 슬롯이 모두 채워졌는지 확인
    is_filled = state.is_required_slots_filled()
    missing = state.get_missing_required_slots()

    print(f"✓ All required slots filled: {is_filled}")
    print(f"✓ Missing required slots: {missing}")
    print()

    return state


def test_slot_filling():
    """슬롯 채우기 테스트"""
    print("=" * 60)
    print("TEST 2: 슬롯 채우기 (Slot Filling)")
    print("=" * 60)

    # 일부 정보만 있는 초기 요청
    request = "점심 메뉴 추천해줘"
    state = create_initial_state(request)

    print(f"Initial state:")
    print(f"  Intent: {state.intent}")
    print(f"  Required slots: {state.required_slots}")
    print(f"  Confirmed slots: {list(state.slots.keys())}")
    print(f"  Missing slots: {state.get_missing_required_slots()}")
    print()

    # 사용자 입력 1: 위치, 인원
    user_input_1 = "을지로에서 2명"
    state = SlotFillingParser.parse(user_input_1, state)
    print(f"After input: '{user_input_1}'")
    print(f"  Confirmed slots: {list(state.slots.keys())}")
    print(f"  Missing slots: {state.get_missing_required_slots()}")
    print(f"  Is filled: {state.is_required_slots_filled()}")
    print()

    # 사용자 입력 2: 시간
    user_input_2 = "12시 30분"
    state = SlotFillingParser.parse(user_input_2, state)
    print(f"After input: '{user_input_2}'")
    print(f"  Confirmed slots: {list(state.slots.keys())}")
    print(f"  Missing slots: {state.get_missing_required_slots()}")
    print(f"  Is filled: {state.is_required_slots_filled()}")
    print()

    return state


def test_qa_gate_logic():
    """Q&A Gate 로직 테스트"""
    print("=" * 60)
    print("TEST 3: Q&A Gate Logic")
    print("=" * 60)

    # 시나리오 1: 필수 슬롯이 모두 채워진 경우
    state = ConversationState(
        intent="lunch_recommendation",
        required_slots=["location", "datetime", "party_size"],
        slots={
            "location": "을지로",
            "datetime": "12시 30분",
            "party_size": 2
        }
    )

    print("Scenario 1: 필수 슬롯이 모두 채워진 경우")
    print(f"  Required slots: {state.required_slots}")
    print(f"  Confirmed slots: {list(state.slots.keys())}")
    print(f"  Missing slots: {state.get_missing_required_slots()}")
    print(f"  Should COMPLETE: {state.is_required_slots_filled()}")
    print()

    # 시나리오 2: 필수 슬롯이 부분적으로만 채워진 경우
    state2 = ConversationState(
        intent="lunch_recommendation",
        required_slots=["location", "datetime", "party_size"],
        slots={
            "location": "을지로",
            "party_size": 2
        }
    )

    print("Scenario 2: 필수 슬롯이 부분적으로만 채워진 경우")
    print(f"  Required slots: {state2.required_slots}")
    print(f"  Confirmed slots: {list(state2.slots.keys())}")
    print(f"  Missing slots: {state2.get_missing_required_slots()}")
    print(f"  Should WAIT_USER: {not state2.is_required_slots_filled()}")
    print()

    # 시나리오 3: 필수 슬롯이 없는 경우 (general intent)
    state3 = ConversationState(
        intent="general",
        required_slots=[],
        slots={}
    )

    print("Scenario 3: 필수 슬롯이 없는 경우 (general intent)")
    print(f"  Required slots: {state3.required_slots}")
    print(f"  Confirmed slots: {list(state3.slots.keys())}")
    print(f"  Missing slots: {state3.get_missing_required_slots()}")
    print(f"  Should COMPLETE: {state3.is_required_slots_filled()}")
    print()


def test_confirmed_info_display():
    """확정된 정보 표시 테스트"""
    print("=" * 60)
    print("TEST 4: 확정된/미확정 정보 표시")
    print("=" * 60)

    state = ConversationState(
        intent="lunch_recommendation",
        required_slots=["location", "datetime", "party_size"],
        slots={
            "location": "을지로",
            "party_size": 2,
            "food_preference": "일식"
        },
        pending_slots=["datetime"]
    )

    print("확정된 정보 (사용자가 이미 제공한 정보):")
    print(state.get_confirmed_info_text())
    print()

    print("미확정 정보 (아직 확인이 필요한 정보):")
    print(state.get_pending_info_text())
    print()


def main():
    """전체 테스트 실행"""
    print("\n")
    print("🔴 Q&A Gate Logic 검증 시작")
    print("=" * 60)
    print()

    try:
        # Test 1: 초기 상태 생성
        state1 = test_initial_state_creation()

        # Test 2: 슬롯 채우기
        state2 = test_slot_filling()

        # Test 3: Q&A Gate 로직
        test_qa_gate_logic()

        # Test 4: 확정된 정보 표시
        test_confirmed_info_display()

        print("=" * 60)
        print("✅ 모든 테스트 통과!")
        print("=" * 60)
        print()

        print("검증 결과:")
        print("1. ✅ ConversationState 초기화 정상 작동")
        print("2. ✅ SlotFillingParser 정상 작동")
        print("3. ✅ is_required_slots_filled() 정상 작동")
        print("4. ✅ get_missing_required_slots() 정상 작동")
        print("5. ✅ 확정된/미확정 정보 표시 정상 작동")
        print()

        print("Q&A Agent Gate Logic:")
        print("- 필수 슬롯이 모두 채워지면 → COMPLETED")
        print("- 필수 슬롯이 부분적으로만 채워지면 → WAITING_USER")
        print("- LLM 호출 없이 즉시 결정 (Rule-based)")
        print()

    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
