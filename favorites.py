"""즐겨찾기 API. 요청 헤더 X-User-Id(익명 기기 ID)로 사용자를 구분한다."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response

from ..campus import CampusService, NotFound
from ..deps import get_campus, get_repo, require_user
from ..repository import Repository
from ..schemas import FacilityOut

router = APIRouter(prefix="/me/favorites", tags=["즐겨찾기"])


@router.get("", response_model=list[FacilityOut], summary="내 즐겨찾기 목록 (추가한 순서)")
def list_favorites(user: str = Depends(require_user), repo: Repository = Depends(get_repo),
                   campus: CampusService = Depends(get_campus)):
    out = []
    for fid in repo.list_favorites(user):
        if fid in campus.facility_by_id:            # 도면 갱신으로 사라진 시설은 건너뜀
            out.append(campus.facility_by_id[fid].to_dict())
    return out


@router.put("/{facility_id}", response_model=FacilityOut, summary="즐겨찾기 추가 (이미 있으면 그대로)",
            responses={201: {"description": "새로 추가함"}, 200: {"description": "이미 있었음"}})
def add_favorite(facility_id: str, response: Response, user: str = Depends(require_user),
                 repo: Repository = Depends(get_repo), campus: CampusService = Depends(get_campus)):
    try:
        fac = campus.facility(facility_id)
    except NotFound as e:
        raise HTTPException(404, str(e))
    response.status_code = 201 if repo.add_favorite(user, facility_id) else 200
    return fac.to_dict()


@router.delete("/{facility_id}", status_code=204, summary="즐겨찾기 삭제")
def remove_favorite(facility_id: str, user: str = Depends(require_user),
                    repo: Repository = Depends(get_repo)):
    if not repo.remove_favorite(user, facility_id):
        raise HTTPException(404, "즐겨찾기에 없는 시설입니다")
    return Response(status_code=204)
