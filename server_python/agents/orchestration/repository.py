#!/usr/bin/env python3
"""
Workflow Repository - 상태 영속성

워크플로우 상태의 영속성을 위한 Repository 패턴 구현입니다.
메모리, 파일, Redis 등 다양한 백엔드를 지원합니다.
"""

import json
import os
from abc import ABC, abstractmethod
from typing import Dict, Optional, List, Any
from datetime import datetime

from .types import DynamicWorkflow, WorkflowPhase, AgentStep, AgentRole


class WorkflowRepository(ABC):
    """
    워크플로우 저장소 추상 클래스

    다양한 백엔드 구현을 위한 인터페이스를 정의합니다.
    """

    @abstractmethod
    async def save(self, workflow: DynamicWorkflow) -> bool:
        """워크플로우 저장"""
        pass

    @abstractmethod
    async def load(self, task_id: str) -> Optional[DynamicWorkflow]:
        """워크플로우 로드"""
        pass

    @abstractmethod
    async def delete(self, task_id: str) -> bool:
        """워크플로우 삭제"""
        pass

    @abstractmethod
    async def list_all(self) -> List[str]:
        """모든 워크플로우 ID 목록"""
        pass

    @abstractmethod
    async def exists(self, task_id: str) -> bool:
        """워크플로우 존재 여부 확인"""
        pass


class InMemoryRepository(WorkflowRepository):
    """
    메모리 기반 저장소

    테스트 및 개발 환경에서 사용합니다.
    """

    def __init__(self):
        self._storage: Dict[str, Dict[str, Any]] = {}

    async def save(self, workflow: DynamicWorkflow) -> bool:
        """워크플로우 저장"""
        try:
            self._storage[workflow.task_id] = workflow.to_dict()
            return True
        except Exception as e:
            print(f"[InMemoryRepository] Save error: {e}")
            return False

    async def load(self, task_id: str) -> Optional[DynamicWorkflow]:
        """워크플로우 로드"""
        data = self._storage.get(task_id)
        if not data:
            return None

        try:
            return self._deserialize(data)
        except Exception as e:
            print(f"[InMemoryRepository] Load error: {e}")
            return None

    async def delete(self, task_id: str) -> bool:
        """워크플로우 삭제"""
        if task_id in self._storage:
            del self._storage[task_id]
            return True
        return False

    async def list_all(self) -> List[str]:
        """모든 워크플로우 ID 목록"""
        return list(self._storage.keys())

    async def exists(self, task_id: str) -> bool:
        """워크플로우 존재 여부 확인"""
        return task_id in self._storage

    def _deserialize(self, data: Dict[str, Any]) -> DynamicWorkflow:
        """딕셔너리에서 워크플로우 역직렬화"""
        steps = [
            AgentStep(
                id=s["id"],
                agent_id=s["agent_id"],
                agent_name=s["agent_name"],
                agent_role=AgentRole(s["agent_role"]),
                description=s["description"],
                order=s["order"],
                status=s.get("status", "pending"),
                result=s.get("result"),
                data=s.get("data"),
                user_input=s.get("user_input"),
                user_prompt=s.get("user_prompt"),
            )
            for s in data.get("steps", [])
        ]

        return DynamicWorkflow(
            task_id=data["task_id"],
            original_request=data["original_request"],
            phase=WorkflowPhase(data.get("phase", "analyzing")),
            steps=steps,
            current_step_index=data.get("current_step_index", 0),
            context=data.get("context", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(),
        )


class FileRepository(WorkflowRepository):
    """
    파일 기반 저장소

    로컬 파일 시스템에 JSON 형태로 저장합니다.
    """

    def __init__(self, storage_dir: str = "./workflow_storage"):
        self._storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

    def _get_file_path(self, task_id: str) -> str:
        """파일 경로 생성"""
        # task_id에서 안전한 파일명 생성
        safe_id = task_id.replace("/", "_").replace("\\", "_")
        return os.path.join(self._storage_dir, f"{safe_id}.json")

    async def save(self, workflow: DynamicWorkflow) -> bool:
        """워크플로우 저장"""
        try:
            file_path = self._get_file_path(workflow.task_id)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(workflow.to_dict(), f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"[FileRepository] Save error: {e}")
            return False

    async def load(self, task_id: str) -> Optional[DynamicWorkflow]:
        """워크플로우 로드"""
        file_path = self._get_file_path(task_id)
        if not os.path.exists(file_path):
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return self._deserialize(data)
        except Exception as e:
            print(f"[FileRepository] Load error: {e}")
            return None

    async def delete(self, task_id: str) -> bool:
        """워크플로우 삭제"""
        file_path = self._get_file_path(task_id)
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False

    async def list_all(self) -> List[str]:
        """모든 워크플로우 ID 목록"""
        files = os.listdir(self._storage_dir)
        return [
            f[:-5]  # .json 제거
            for f in files
            if f.endswith('.json')
        ]

    async def exists(self, task_id: str) -> bool:
        """워크플로우 존재 여부 확인"""
        file_path = self._get_file_path(task_id)
        return os.path.exists(file_path)

    def _deserialize(self, data: Dict[str, Any]) -> DynamicWorkflow:
        """딕셔너리에서 워크플로우 역직렬화"""
        steps = [
            AgentStep(
                id=s["id"],
                agent_id=s["agent_id"],
                agent_name=s["agent_name"],
                agent_role=AgentRole(s["agent_role"]),
                description=s["description"],
                order=s["order"],
                status=s.get("status", "pending"),
                result=s.get("result"),
                data=s.get("data"),
                user_input=s.get("user_input"),
                user_prompt=s.get("user_prompt"),
            )
            for s in data.get("steps", [])
        ]

        return DynamicWorkflow(
            task_id=data["task_id"],
            original_request=data["original_request"],
            phase=WorkflowPhase(data.get("phase", "analyzing")),
            steps=steps,
            current_step_index=data.get("current_step_index", 0),
            context=data.get("context", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(),
        )


class RedisRepository(WorkflowRepository):
    """
    Redis 기반 저장소

    분산 환경에서 사용합니다.
    redis-py 라이브러리가 필요합니다.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        key_prefix: str = "workflow:"
    ):
        self._host = host
        self._port = port
        self._db = db
        self._key_prefix = key_prefix
        self._client = None

    async def _get_client(self):
        """Redis 클라이언트 획득"""
        if self._client is None:
            try:
                import redis.asyncio as redis
                self._client = redis.Redis(
                    host=self._host,
                    port=self._port,
                    db=self._db,
                    decode_responses=True
                )
            except ImportError:
                raise ImportError("redis package is required for RedisRepository")
        return self._client

    def _get_key(self, task_id: str) -> str:
        """Redis 키 생성"""
        return f"{self._key_prefix}{task_id}"

    async def save(self, workflow: DynamicWorkflow) -> bool:
        """워크플로우 저장"""
        try:
            client = await self._get_client()
            key = self._get_key(workflow.task_id)
            data = json.dumps(workflow.to_dict(), ensure_ascii=False)
            await client.set(key, data)
            return True
        except Exception as e:
            print(f"[RedisRepository] Save error: {e}")
            return False

    async def load(self, task_id: str) -> Optional[DynamicWorkflow]:
        """워크플로우 로드"""
        try:
            client = await self._get_client()
            key = self._get_key(task_id)
            data = await client.get(key)
            if not data:
                return None
            return self._deserialize(json.loads(data))
        except Exception as e:
            print(f"[RedisRepository] Load error: {e}")
            return None

    async def delete(self, task_id: str) -> bool:
        """워크플로우 삭제"""
        try:
            client = await self._get_client()
            key = self._get_key(task_id)
            result = await client.delete(key)
            return result > 0
        except Exception as e:
            print(f"[RedisRepository] Delete error: {e}")
            return False

    async def list_all(self) -> List[str]:
        """모든 워크플로우 ID 목록"""
        try:
            client = await self._get_client()
            keys = await client.keys(f"{self._key_prefix}*")
            return [
                k.replace(self._key_prefix, "")
                for k in keys
            ]
        except Exception as e:
            print(f"[RedisRepository] List error: {e}")
            return []

    async def exists(self, task_id: str) -> bool:
        """워크플로우 존재 여부 확인"""
        try:
            client = await self._get_client()
            key = self._get_key(task_id)
            return await client.exists(key) > 0
        except Exception as e:
            print(f"[RedisRepository] Exists error: {e}")
            return False

    def _deserialize(self, data: Dict[str, Any]) -> DynamicWorkflow:
        """딕셔너리에서 워크플로우 역직렬화"""
        steps = [
            AgentStep(
                id=s["id"],
                agent_id=s["agent_id"],
                agent_name=s["agent_name"],
                agent_role=AgentRole(s["agent_role"]),
                description=s["description"],
                order=s["order"],
                status=s.get("status", "pending"),
                result=s.get("result"),
                data=s.get("data"),
                user_input=s.get("user_input"),
                user_prompt=s.get("user_prompt"),
            )
            for s in data.get("steps", [])
        ]

        return DynamicWorkflow(
            task_id=data["task_id"],
            original_request=data["original_request"],
            phase=WorkflowPhase(data.get("phase", "analyzing")),
            steps=steps,
            current_step_index=data.get("current_step_index", 0),
            context=data.get("context", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(),
        )


# Repository Factory
def create_repository(
    backend: str = "memory",
    **kwargs
) -> WorkflowRepository:
    """
    Repository 팩토리 함수

    Args:
        backend: 백엔드 유형 ("memory", "file", "redis")
        **kwargs: 백엔드별 설정

    Returns:
        WorkflowRepository 구현체
    """
    if backend == "memory":
        return InMemoryRepository()
    elif backend == "file":
        return FileRepository(
            storage_dir=kwargs.get("storage_dir", "./workflow_storage")
        )
    elif backend == "redis":
        return RedisRepository(
            host=kwargs.get("host", "localhost"),
            port=kwargs.get("port", 6379),
            db=kwargs.get("db", 0),
            key_prefix=kwargs.get("key_prefix", "workflow:")
        )
    else:
        raise ValueError(f"Unknown repository backend: {backend}")
