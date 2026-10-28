"""지도 조회 API: 건물·층·시설·노드·검색."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ..campus import CampusService, NotFound
from ..deps import get_campus
from ..domain import Category
from ..schemas import BuildingOut, FacilityOut, FloorOut, NodeOut

router = APIRouter(tags=["지도"])


def _building_out(b) -> dict:
    return {"buildingId": b.building_id, "name": b.name,
            "floors": [{"level": fl.level, "label": fl.label} for fl in b.floors]}


@router.get("/buildings", response_model=list[BuildingOut], summary="서비스 구역 건물 목록")
def list_buildings(campus: CampusService = Depends(get_campus)):
    return [_building_out(b) for b in campus.buildings.values()]


@router.get("/buildings/{building_id}", response_model=BuildingOut, summary="건물 하나")
def get_building(building_id: str, campus: CampusService = Depends(get_campus)):
    try:
        return _building_out(campus.building(building_id))
    except NotFound as e:
        raise HTTPException(404, str(e))


@router.get("/buildings/{building_id}/floors/{level}", response_model=FloorOut,
            summary="층 도면(SVG 경로)과 그 층의 시설")
def get_floor(building_id: str, level: int, campus: CampusService = Depends(get_campus)):
    try:
        fl = campus.building(building_id).get_floor(level)
    except (NotFound, KeyError) as e:
        raise HTTPException(404, str(e).strip("'\""))
    return {"buildingId": building_id, "level": fl.level, "label": fl.label, "svgUrl": fl.svg_url,
            "facilities": [f.to_dict() for f in fl.get_facilities()]}


@router.get("/buildings/{building_id}/floors/{level}/nodes", response_model=list[NodeOut],
            summary="층의 길찾기 노드 (경로 그리기·디버깅용)")
def get_floor_nodes(building_id: str, level: int, campus: CampusService = Depends(get_campus)):
    try:
        return [n.to_dict() for n in campus.floor_nodes(building_id, level)]
    except (NotFound, KeyError) as e:
        raise HTTPException(404, str(e).strip("'\""))


@router.get("/nodes/nearest", response_model=NodeOut, summary="지도에서 찍은 위치와 가장 가까운 노드")
def nearest_node(building_id: str, floor: int, x: float, y: float,
                 campus: CampusService = Depends(get_campus)):
    try:
        return campus.nearest_node(building_id, floor, x, y).to_dict()
    except (NotFound, KeyError) as e:
        raise HTTPException(404, str(e).strip("'\""))


@router.get("/search", response_model=list[FacilityOut], summary="시설 검색 (호실·이름·초성)")
def search(q: str = Query(..., min_length=1, max_length=50), limit: int = Query(10, ge=1, le=50),
           campus: CampusService = Depends(get_campus)):
    return [f.to_dict() for f in campus.search_service.search(q, limit)]


@router.get("/facilities", response_model=list[FacilityOut], summary="카테고리·건물·층으로 시설 필터")
def filter_facilities(category: Category | None = None, building_id: str | None = None,
                      floor: int | None = None, campus: CampusService = Depends(get_campus)):
    return [f.to_dict() for f in campus.facilities_where(category, building_id, floor)]


@router.get("/facilities/{facility_id}", response_model=FacilityOut, summary="시설 상세")
def get_facility(facility_id: str, campus: CampusService = Depends(get_campus)):
    try:
        return campus.facility(facility_id).to_dict()
    except NotFound as e:
        raise HTTPException(404, str(e))
