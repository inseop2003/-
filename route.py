"""길찾기 API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..campus import CampusService, NotFound
from ..deps import get_campus
from ..route_finder import NoRouteError
from ..schemas import RouteOut

router = APIRouter(tags=["길찾기"])


@router.get("/route", response_model=RouteOut, summary="최단 경로 / 배리어프리 경로",
            responses={404: {"description": "시설·노드가 없거나 경로가 없음"}})
def route(start: str, end: str, barrier_free: bool = False,
          campus: CampusService = Depends(get_campus)):
    """`start`, `end`에는 시설 ID(F_4_5401)나 노드 ID(1F_정문)를 넣는다.

    - `barrier_free=true`면 계단 노드를 뺀 그래프에서 찾는다 (엘리베이터·경사로만 사용).
    - 출발·도착 건물이 다르면 `legs`가 [실내, 실외, 실내] 세 구간으로 나온다.
      실외 구간은 아직 지도 데이터가 없어 거리가 null이다.
    """
    try:
        return campus.route(start, end, barrier_free)
    except (NotFound, NoRouteError) as e:
        raise HTTPException(404, str(e))
