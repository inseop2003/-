"""지름길 게시판 API: 학생들이 아는 빠른 길을 글로 공유하고 좋아요로 추천한다."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from ..campus import CampusService
from ..deps import get_campus, get_repo, optional_user, require_user
from ..repository import Repository
from ..schemas import LikeOut, ShortcutIn, ShortcutOut, ShortcutPage

router = APIRouter(prefix="/shortcuts", tags=["지름길 게시판"])


def _out(row, campus: CampusService, liked: set[int], user: str | None) -> dict:
    def fac(fid):
        f = campus.facility_by_id.get(fid) if fid else None
        return f.to_dict() if f else None
    return {"shortcutId": row["shortcut_id"], "buildingId": row["building_id"],
            "title": row["title"], "body": row["body"],
            "fromFacility": fac(row["from_facility_id"]), "toFacility": fac(row["to_facility_id"]),
            "createdAt": row["created_at"], "likeCount": row["like_count"],
            "likedByMe": row["shortcut_id"] in liked, "mine": user is not None and row["author_id"] == user}


def _get_or_404(repo: Repository, shortcut_id: int):
    row = repo.get_shortcut(shortcut_id)
    if row is None:
        raise HTTPException(404, "게시글이 없습니다")
    return row


@router.get("", response_model=ShortcutPage, summary="게시글 목록")
def list_shortcuts(building_id: str | None = None,
                   sort: Literal["recent", "popular"] = "recent",
                   limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
                   user: str | None = Depends(optional_user), repo: Repository = Depends(get_repo),
                   campus: CampusService = Depends(get_campus)):
    rows, total = repo.list_shortcuts(building_id, sort, limit, offset)
    liked = repo.liked_by([r["shortcut_id"] for r in rows], user)
    return {"total": total, "items": [_out(r, campus, liked, user) for r in rows]}


@router.get("/{shortcut_id}", response_model=ShortcutOut, summary="게시글 하나")
def get_shortcut(shortcut_id: int, user: str | None = Depends(optional_user),
                 repo: Repository = Depends(get_repo), campus: CampusService = Depends(get_campus)):
    row = _get_or_404(repo, shortcut_id)
    return _out(row, campus, repo.liked_by([shortcut_id], user), user)


@router.post("", response_model=ShortcutOut, status_code=201, summary="게시글 쓰기")
def create_shortcut(body: ShortcutIn, user: str = Depends(require_user),
                    repo: Repository = Depends(get_repo), campus: CampusService = Depends(get_campus)):
    if body.buildingId not in campus.buildings:
        raise HTTPException(422, f"건물이 없습니다: {body.buildingId}")
    for fid in (body.fromFacilityId, body.toFacilityId):
        if fid is not None and fid not in campus.facility_by_id:
            raise HTTPException(422, f"시설이 없습니다: {fid}")
    title, text = body.title.strip(), body.body.strip()
    if not title or not text:
        raise HTTPException(422, "제목과 내용을 입력하세요")
    sid = repo.create_shortcut(user, body.buildingId, title, text, body.fromFacilityId, body.toFacilityId)
    return _out(repo.get_shortcut(sid), campus, set(), user)


@router.post("/{shortcut_id}/like", response_model=LikeOut, summary="좋아요 켜기/끄기")
def toggle_like(shortcut_id: int, user: str = Depends(require_user), repo: Repository = Depends(get_repo)):
    _get_or_404(repo, shortcut_id)
    liked, count = repo.toggle_like(shortcut_id, user)
    return {"liked": liked, "likeCount": count}


@router.delete("/{shortcut_id}", status_code=204, summary="내 게시글 삭제")
def delete_shortcut(shortcut_id: int, user: str = Depends(require_user), repo: Repository = Depends(get_repo)):
    row = _get_or_404(repo, shortcut_id)
    if row["author_id"] != user:
        raise HTTPException(403, "본인이 쓴 글만 지울 수 있습니다")
    repo.delete_shortcut(shortcut_id)
    return Response(status_code=204)
