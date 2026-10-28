"""환경 설정. 모든 값은 환경 변수로 바꿀 수 있다.

MYONGJIMAP_DB            SQLite 파일 경로 (기본 :memory: — 재시작하면 즐겨찾기·게시글 사라짐)
MYONGJIMAP_CORS_ORIGINS  쉼표로 구분한 허용 출처 (기본 *)
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    db_path: str = field(default_factory=lambda: os.environ.get("MYONGJIMAP_DB", ":memory:"))
    cors_origins: tuple[str, ...] = field(default_factory=lambda: tuple(
        o.strip() for o in os.environ.get("MYONGJIMAP_CORS_ORIGINS", "*").split(",") if o.strip()))

    # 도면 1단위 = 몇 m 인가 (건물별). 현재 도면은 안내도 사진을 따라 그린 근사값이라
    # 축척을 아직 모른다 → None 이면 거리를 '도면 단위'로만 내보낸다.
    # 실측 후 예: {"ENG5": 0.1} 처럼 채우면 distanceMeters·예상 시간이 함께 나간다.
    meters_per_unit: dict[str, float | None] = field(default_factory=lambda: {
        "ENG5": None, "CHANGJO": None, "HAMBAK": None})

    walking_speed_mps: float = 1.2          # 보행 속도 (m/s)
    max_title_len: int = 60
    max_body_len: int = 1000


settings = Settings()
