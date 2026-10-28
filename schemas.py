"""API 요청·응답 모델 (Pydantic). /docs 화면에 그대로 문서로 나온다.

필드 이름은 프론트엔드(JavaScript)에 맞춰 camelCase로 쓴다.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .config import settings


# ---------------- 지도 ----------------
class FloorSummary(BaseModel):
    level: int = Field(description="층 (지하 1층 = -1)")
    label: str = Field(description="표시용 이름 (B1F, 1F …)")


class BuildingOut(BaseModel):
    buildingId: str
    name: str
    floors: list[FloorSummary]


class FacilityOut(BaseModel):
    facilityId: str
    name: str
    category: str
    x: float
    y: float
    nodeId: str | None
    buildingId: str | None
    floor: int | None
    info: str
    roomNumber: str | None = None
    hasComputerLab: bool | None = None
    hasOutlet: bool | None = None


class FloorOut(BaseModel):
    buildingId: str
    level: int
    label: str
    svgUrl: str
    facilities: list[FacilityOut]


class NodeOut(BaseModel):
    nodeId: str
    buildingId: str
    floor: int
    x: float
    y: float
    type: str


# ---------------- 길찾기 ----------------
class FloorChange(BaseModel):
    at: str
    via: str
    fromFloor: int
    toFloor: int


class Step(BaseModel):
    type: Literal["START", "WALK", "FLOOR_CHANGE", "EXIT", "OUTDOOR", "ENTER", "ARRIVE"]
    nodeId: str
    floor: int
    text: str
    via: str | None = None


class Leg(BaseModel):
    kind: Literal["INDOOR", "OUTDOOR"]
    buildingId: str | None = None
    fromNodeId: str | None = None
    toNodeId: str | None = None
    fromBuildingId: str | None = None
    toBuildingId: str | None = None
    distance: float | None
    distanceMeters: float | None
    path: list[NodeOut] = []
    floorChanges: list[FloorChange] = []
    steps: list[Step]


class RouteOut(BaseModel):
    barrierFree: bool
    crossBuilding: bool
    distance: float = Field(description="실내 구간 거리 합 (도면 단위)")
    distanceMeters: float | None = Field(description="축척이 설정된 건물만 m로 환산, 아니면 null")
    etaSeconds: int | None
    legs: list[Leg]
    path: list[NodeOut]
    floorChanges: list[FloorChange]
    steps: list[Step]


# ---------------- 즐겨찾기 ----------------
class FavoriteOut(BaseModel):
    facility: FacilityOut


# ---------------- 지름길 게시판 ----------------
class ShortcutIn(BaseModel):
    buildingId: str
    title: str = Field(min_length=1, max_length=settings.max_title_len)
    body: str = Field(min_length=1, max_length=settings.max_body_len)
    fromFacilityId: str | None = None
    toFacilityId: str | None = None


class ShortcutOut(BaseModel):
    shortcutId: int
    buildingId: str
    title: str
    body: str
    fromFacility: FacilityOut | None
    toFacility: FacilityOut | None
    createdAt: str
    likeCount: int
    likedByMe: bool
    mine: bool


class ShortcutPage(BaseModel):
    total: int
    items: list[ShortcutOut]


class LikeOut(BaseModel):
    liked: bool
    likeCount: int


class ErrorOut(BaseModel):
    detail: str
