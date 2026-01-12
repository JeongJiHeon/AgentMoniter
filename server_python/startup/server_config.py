"""
ServerConfig - FastAPI 및 서버 설정

FastAPI 앱 생성 및 CORS 설정을 담당합니다.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def create_fastapi_app(title: str = "Agent Monitor API") -> FastAPI:
    """
    FastAPI 앱 생성

    Args:
        title: API 제목

    Returns:
        FastAPI 앱 인스턴스
    """
    app = FastAPI(title=title)
    setup_cors(app)
    return app


def setup_cors(
    app: FastAPI,
    allow_origins: list = None,
    allow_credentials: bool = True,
    allow_methods: list = None,
    allow_headers: list = None
):
    """
    CORS 미들웨어 설정

    Args:
        app: FastAPI 앱
        allow_origins: 허용할 origin 목록 (기본: ["*"])
        allow_credentials: 자격 증명 허용 여부
        allow_methods: 허용할 HTTP 메서드 (기본: ["*"])
        allow_headers: 허용할 헤더 (기본: ["*"])
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins or ["*"],
        allow_credentials=allow_credentials,
        allow_methods=allow_methods or ["*"],
        allow_headers=allow_headers or ["*"],
    )
