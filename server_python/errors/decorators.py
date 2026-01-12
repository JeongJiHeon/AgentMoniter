"""
Decorators - 에러 핸들링 데코레이터

함수에 적용하여 자동으로 에러를 처리하는 데코레이터입니다.
"""

import functools
import traceback
from typing import Callable, Optional, TypeVar, Any

from .exceptions import AgentMonitorError
from .error_response import ErrorResponse


T = TypeVar('T')


def handle_errors(
    default_return: Any = None,
    log_errors: bool = True,
    reraise: bool = False
):
    """
    동기 함수용 에러 핸들링 데코레이터

    Args:
        default_return: 에러 발생 시 반환할 기본값
        log_errors: 에러 로깅 여부
        reraise: 에러 재발생 여부

    Example:
        @handle_errors(default_return=None)
        def get_agent(agent_id):
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except AgentMonitorError as e:
                if log_errors:
                    print(f"[{func.__name__}] Error: {e.code} - {e.message}")
                if reraise:
                    raise
                return default_return
            except Exception as e:
                if log_errors:
                    print(f"[{func.__name__}] Unexpected error: {e}")
                    traceback.print_exc()
                if reraise:
                    raise
                return default_return
        return wrapper
    return decorator


def async_handle_errors(
    default_return: Any = None,
    log_errors: bool = True,
    reraise: bool = False,
    broadcast_error: bool = False,
    ws_server_getter: Optional[Callable] = None
):
    """
    비동기 함수용 에러 핸들링 데코레이터

    Args:
        default_return: 에러 발생 시 반환할 기본값
        log_errors: 에러 로깅 여부
        reraise: 에러 재발생 여부
        broadcast_error: WebSocket으로 에러 브로드캐스트 여부
        ws_server_getter: WebSocket 서버 인스턴스를 반환하는 함수

    Example:
        @async_handle_errors(default_return=None, broadcast_error=True)
        async def process_task(task_id):
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            try:
                return await func(*args, **kwargs)
            except AgentMonitorError as e:
                if log_errors:
                    print(f"[{func.__name__}] Error: {e.code} - {e.message}")

                if broadcast_error and ws_server_getter:
                    try:
                        ws_server = ws_server_getter()
                        if ws_server:
                            error_response = ErrorResponse.from_exception(e)
                            ws_server.broadcast_notification(
                                f"Error: {e.message}",
                                "error"
                            )
                    except Exception:
                        pass

                if reraise:
                    raise
                return default_return

            except Exception as e:
                if log_errors:
                    print(f"[{func.__name__}] Unexpected error: {e}")
                    traceback.print_exc()

                if broadcast_error and ws_server_getter:
                    try:
                        ws_server = ws_server_getter()
                        if ws_server:
                            ws_server.broadcast_notification(
                                f"Unexpected error: {str(e)}",
                                "error"
                            )
                    except Exception:
                        pass

                if reraise:
                    raise
                return default_return
        return wrapper
    return decorator


class ErrorHandler:
    """
    클래스 기반 에러 핸들러

    컨텍스트 매니저로 사용하여 에러를 처리합니다.

    Example:
        async with ErrorHandler(ws_server) as handler:
            result = await risky_operation()
            if handler.has_error:
                return handler.error_response
    """

    def __init__(
        self,
        ws_server=None,
        log_errors: bool = True,
        broadcast_errors: bool = False
    ):
        self.ws_server = ws_server
        self.log_errors = log_errors
        self.broadcast_errors = broadcast_errors
        self.error: Optional[Exception] = None
        self.error_response: Optional[ErrorResponse] = None

    @property
    def has_error(self) -> bool:
        return self.error is not None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None:
            self.error = exc_val
            self.error_response = ErrorResponse.from_exception(exc_val)

            if self.log_errors:
                if isinstance(exc_val, AgentMonitorError):
                    print(f"[ErrorHandler] {exc_val.code}: {exc_val.message}")
                else:
                    print(f"[ErrorHandler] Unexpected error: {exc_val}")
                    traceback.print_exc()

            if self.broadcast_errors and self.ws_server:
                self.ws_server.broadcast_notification(
                    f"Error: {str(exc_val)}",
                    "error"
                )

            # 예외를 삼킴 (False 반환 시 예외 전파)
            return True

        return False
