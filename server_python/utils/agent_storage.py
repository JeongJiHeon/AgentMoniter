"""
Agent 영구 저장 유틸리티

Agent를 JSON 파일에 저장하고 로드합니다.
"""
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from agents.types import AgentConfig


# 데이터 디렉토리
DATA_DIR = Path(__file__).parent.parent / "data"
AGENTS_FILE = DATA_DIR / "agents.json"


def ensure_data_dir():
    """데이터 디렉토리 생성"""
    DATA_DIR.mkdir(exist_ok=True)


def save_agents(agents: List[Dict[str, Any]]) -> None:
    """Agent 목록을 파일에 저장"""
    ensure_data_dir()
    
    try:
        with open(AGENTS_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                "version": "1.0",
                "updatedAt": datetime.now().isoformat(),
                "agents": agents
            }, f, indent=2, ensure_ascii=False)
        print(f"[AgentStorage] Saved {len(agents)} agents to {AGENTS_FILE}")
    except Exception as e:
        print(f"[AgentStorage] Error saving agents: {e}")
        import traceback
        traceback.print_exc()


def load_agents() -> List[Dict[str, Any]]:
    """파일에서 Agent 목록 로드"""
    if not AGENTS_FILE.exists():
        print(f"[AgentStorage] Agents file not found: {AGENTS_FILE}")
        return []
    
    try:
        with open(AGENTS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            agents = data.get("agents", [])
            print(f"[AgentStorage] Loaded {len(agents)} agents from {AGENTS_FILE}")
            return agents
    except Exception as e:
        print(f"[AgentStorage] Error loading agents: {e}")
        import traceback
        traceback.print_exc()
        return []


def save_agent_config(agent_id: str, config: AgentConfig, agent_state: Optional[Dict[str, Any]] = None) -> None:
    """단일 Agent 설정 저장"""
    agents = load_agents()
    
    # 기존 Agent 찾기
    existing_index = next((i for i, a in enumerate(agents) if a.get("id") == agent_id), None)
    
    agent_data = {
        "id": agent_id,
        "name": config.name,
        "type": config.type,
        "description": config.description,
        "constraints": config.constraints or [],
        "permissions": config.permissions or {},
        "customConfig": config.custom_config or {},
        "createdAt": datetime.now().isoformat(),
        "updatedAt": datetime.now().isoformat(),
    }
    
    if agent_state:
        agent_data["state"] = agent_state
    
    if existing_index is not None:
        # 기존 Agent 업데이트
        agents[existing_index] = agent_data
    else:
        # 새 Agent 추가
        agents.append(agent_data)
    
    save_agents(agents)


def delete_agent(agent_id: str) -> None:
    """Agent 삭제"""
    agents = load_agents()
    agents = [a for a in agents if a.get("id") != agent_id]
    save_agents(agents)
    print(f"[AgentStorage] Deleted agent: {agent_id}")

