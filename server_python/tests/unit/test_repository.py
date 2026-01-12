"""
Repository Unit Tests

상태 영속성(Repository 패턴)의 단위 테스트입니다.
"""

import pytest
import asyncio
import tempfile
import shutil
import os
from datetime import datetime
from uuid import uuid4

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from agents.orchestration.repository import (
    InMemoryRepository,
    FileRepository,
    create_repository,
)
from agents.orchestration.types import (
    DynamicWorkflow,
    AgentStep,
    AgentRole,
    WorkflowPhase,
)


def make_workflow(task_id: str = None, request: str = "테스트 요청") -> DynamicWorkflow:
    """테스트용 워크플로우 생성"""
    task_id = task_id or f"task-{uuid4()}"
    return DynamicWorkflow(
        task_id=task_id,
        original_request=request,
        phase=WorkflowPhase.ANALYZING,
        steps=[
            AgentStep(
                id=str(uuid4()),
                agent_id="agent-1",
                agent_name="Test Agent 1",
                agent_role=AgentRole.WORKER,
                description="테스트 작업",
                order=1
            )
        ],
        current_step_index=0,
        context={}
    )


class TestInMemoryRepository:
    """InMemoryRepository 테스트"""

    @pytest.fixture
    def repository(self):
        """InMemoryRepository 인스턴스"""
        return InMemoryRepository()

    @pytest.mark.asyncio
    async def test_save_and_load(self, repository):
        """저장 및 로드 테스트"""
        workflow = make_workflow("task-123", "테스트 요청입니다")

        # 저장
        result = await repository.save(workflow)
        assert result is True

        # 로드
        loaded = await repository.load("task-123")
        assert loaded is not None
        assert loaded.task_id == "task-123"
        assert loaded.original_request == "테스트 요청입니다"

    @pytest.mark.asyncio
    async def test_load_nonexistent(self, repository):
        """존재하지 않는 워크플로우 로드"""
        loaded = await repository.load("nonexistent-task")
        assert loaded is None

    @pytest.mark.asyncio
    async def test_delete(self, repository):
        """삭제 테스트"""
        workflow = make_workflow("task-123")
        await repository.save(workflow)

        # 삭제
        result = await repository.delete("task-123")
        assert result is True

        # 삭제 확인
        loaded = await repository.load("task-123")
        assert loaded is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, repository):
        """존재하지 않는 워크플로우 삭제"""
        result = await repository.delete("nonexistent-task")
        assert result is False

    @pytest.mark.asyncio
    async def test_exists(self, repository):
        """존재 여부 확인"""
        workflow = make_workflow("task-123")

        assert await repository.exists("task-123") is False

        await repository.save(workflow)

        assert await repository.exists("task-123") is True

    @pytest.mark.asyncio
    async def test_list_all(self, repository):
        """전체 목록 조회"""
        # 초기 상태
        all_ids = await repository.list_all()
        assert len(all_ids) == 0

        # 저장 후
        workflow = make_workflow("task-123")
        await repository.save(workflow)
        all_ids = await repository.list_all()
        assert len(all_ids) == 1
        assert "task-123" in all_ids


class TestFileRepository:
    """FileRepository 테스트"""

    @pytest.fixture
    def temp_dir(self):
        """임시 디렉토리 생성"""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)

    @pytest.fixture
    def repository(self, temp_dir):
        """FileRepository 인스턴스"""
        return FileRepository(storage_dir=temp_dir)

    @pytest.mark.asyncio
    async def test_save_creates_file(self, repository, temp_dir):
        """저장 시 파일 생성 확인"""
        workflow = make_workflow("task-456")
        await repository.save(workflow)

        file_path = os.path.join(temp_dir, "task-456.json")
        assert os.path.exists(file_path)

    @pytest.mark.asyncio
    async def test_save_and_load(self, repository):
        """저장 및 로드 테스트"""
        workflow = make_workflow("task-456", "파일 저장 테스트")
        await repository.save(workflow)

        loaded = await repository.load("task-456")

        assert loaded is not None
        assert loaded.task_id == "task-456"
        assert loaded.original_request == "파일 저장 테스트"

    @pytest.mark.asyncio
    async def test_delete_removes_file(self, repository, temp_dir):
        """삭제 시 파일 제거 확인"""
        workflow = make_workflow("task-456")
        await repository.save(workflow)

        file_path = os.path.join(temp_dir, "task-456.json")
        assert os.path.exists(file_path)

        await repository.delete("task-456")

        assert not os.path.exists(file_path)


class TestCreateRepository:
    """create_repository 팩토리 함수 테스트"""

    def test_create_memory_repository(self):
        """메모리 저장소 생성"""
        repo = create_repository("memory")
        assert isinstance(repo, InMemoryRepository)

    def test_create_file_repository(self):
        """파일 저장소 생성"""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = create_repository("file", storage_dir=temp_dir)
            assert isinstance(repo, FileRepository)

    def test_create_default_repository(self):
        """기본 저장소 생성"""
        repo = create_repository()
        assert isinstance(repo, InMemoryRepository)

    def test_invalid_repository_type(self):
        """잘못된 저장소 타입"""
        with pytest.raises(ValueError):
            create_repository("invalid_type")
