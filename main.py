"""FastAPI 서버: 프론트엔드 MapController가 호출하는 REST API.

실행:  uvicorn app.main:app --reload   (backend 폴더에서)
문서:  http://localhost:8000/docs

구조
  api/        라우터 (지도·길찾기·즐겨찾기·지름길 게시판)
  campus.py   서비스 계층 (검색·길찾기·건물 간 경로)
  domain.py · graph.py · route_finder.py · search_service.py   도메인·알고리즘 (클래스 다이어그램)
  repository.py   SQLite 저장소
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import routers
from .campus import CampusService
from .campus_data import CAMPUS
from .config import Settings, settings as default_settings
from .repository import Repository


def create_app(settings: Settings | None = None, seed_data: dict | None = None) -> FastAPI:
    """앱을 만든다. 테스트에서는 create_app(Settings(db_path=":memory:"))로 깨끗한 앱을 얻는다."""
    settings = settings or default_settings
    app = FastAPI(title="명지맵 API", version="0.2.0",
                  description="명지대 자연캠퍼스 실내 길찾기 (5공학관 · 창조관 · 함박관)")
    app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins),
                       allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["*"])

    # 시작 시 DB → 도메인 객체 로드 (지도 데이터는 읽기 전용이라 메모리에 둔다)
    repo = Repository(settings.db_path)
    if repo.is_empty():
        repo.seed(seed_data or CAMPUS)
    app.state.repo = repo
    app.state.campus = CampusService(repo.load_buildings(), repo.load_graph(), settings)

    for r in routers:
        app.include_router(r)

    @app.get("/health", tags=["상태"], summary="서버·데이터 상태")
    def health():
        c = app.state.campus
        return {"status": "ok", "buildings": len(c.buildings), "facilities": len(c.facilities),
                "nodes": len(c.graph)}

    return app


app = create_app()
