"""라우터가 공통으로 쓰는 의존성 (서비스 객체, 사용자 ID)."""
from __future__ import annotations

import re

from fastapi import Header, HTTPException, Request

from .campus import CampusService
from .repository import Repository

_USER_ID = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


def get_campus(request: Request) -> CampusService:
    return request.app.state.campus


def get_repo(request: Request) -> Repository:
    return request.app.state.repo


def _check(user_id: str) -> str:
    if not _USER_ID.match(user_id):
        raise HTTPException(400, "X-User-Id는 영문·숫자·-·_ 8~64자여야 합니다")
    return user_id


def require_user(x_user_id: str = Header(..., description="프론트엔드가 만든 익명 기기 ID (UUID 등)")) -> str:
    """로그인 대신 쓰는 익명 사용자 ID. 학교 계정 로그인을 붙이면 이 함수만 바꾸면 된다."""
    return _check(x_user_id)


def optional_user(x_user_id: str | None = Header(None)) -> str | None:
    return _check(x_user_id) if x_user_id else None
