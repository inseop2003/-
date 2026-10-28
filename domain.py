"""도메인 엔티티 모델 (보고서 II-3-1)

Building ◆─ Floor ◆─ Facility(추상) ◁─ Classroom / Amenity
Facility ─> Point, Category
"""
from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


@dataclass(frozen=True)
class Point:
    """SVG 평면도 위의 2D 좌표."""
    x: float
    y: float

    def distance_to(self, other: "Point") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)


class Category(str, Enum):
    """시설 유형 (카테고리 필터 버튼과 1:1 대응)."""
    CLASSROOM = "CLASSROOM"
    CAFE = "CAFE"
    CONVENIENCE = "CONVENIENCE"
    PRINTER = "PRINTER"
    RESTROOM = "RESTROOM"
    STUDY_SPACE = "STUDY_SPACE"
    ELEVATOR = "ELEVATOR"
    OFFICE = "OFFICE"
    CAFETERIA = "CAFETERIA"


class Facility(ABC):
    """건물 안 모든 장소의 상위 추상 클래스."""

    def __init__(self, facility_id: str, name: str, location: Point,
                 category: Category, node_id: str | None = None):
        self.facility_id = facility_id
        self.name = name
        self.location = location
        self.category = category
        # 길찾기 그래프에서 이 시설과 연결된 노드 (없으면 경로 탐색 불가)
        self.node_id = node_id
        self.building_id: str | None = None
        self.floor_level: int | None = None

    @abstractmethod
    def get_info(self) -> str:
        """팝업에 표시할 한 줄 설명."""

    def to_dict(self) -> dict:
        return {
            "facilityId": self.facility_id,
            "name": self.name,
            "category": self.category.value,
            "x": self.location.x,
            "y": self.location.y,
            "nodeId": self.node_id,
            "buildingId": self.building_id,
            "floor": self.floor_level,
            "info": self.get_info(),
        }

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.facility_id!r}, {self.name!r})"


class Classroom(Facility):
    def __init__(self, facility_id: str, name: str, location: Point, room_number: str,
                 has_computer_lab: bool = False, node_id: str | None = None):
        super().__init__(facility_id, name, location, Category.CLASSROOM, node_id)
        self._room_number = room_number
        self.has_computer_lab = has_computer_lab

    def get_room_number(self) -> str:
        return self._room_number

    def get_info(self) -> str:
        lab = " · 컴퓨터 실습실" if self.has_computer_lab else ""
        return f"{self._room_number} 강의실{lab}"

    def to_dict(self) -> dict:
        d = super().to_dict()
        d.update(roomNumber=self._room_number, hasComputerLab=self.has_computer_lab)
        return d


class Amenity(Facility):
    """카페·프린터·화장실·자습공간 등 편의시설."""

    def __init__(self, facility_id: str, name: str, location: Point, category: Category,
                 has_outlet: bool = False, node_id: str | None = None):
        if category is Category.CLASSROOM:
            raise ValueError("강의실은 Classroom으로 만드세요")
        super().__init__(facility_id, name, location, category, node_id)
        self._has_outlet = has_outlet

    def has_outlet(self) -> bool:
        return self._has_outlet

    def get_info(self) -> str:
        outlet = " · 콘센트 있음" if self._has_outlet else ""
        return f"{self.name}{outlet}"

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["hasOutlet"] = self._has_outlet
        return d


@dataclass
class Floor:
    level: int                      # 지하 1층 = -1
    svg_url: str
    facilities: list[Facility] = field(default_factory=list)

    @property
    def label(self) -> str:
        return f"B{-self.level}F" if self.level < 0 else f"{self.level}F"

    def add_facility(self, facility: Facility) -> None:
        facility.floor_level = self.level
        self.facilities.append(facility)

    def get_facilities(self) -> list[Facility]:
        return list(self.facilities)

    def filter_by(self, category: Category) -> list[Facility]:
        return [f for f in self.facilities if f.category is category]


@dataclass
class Building:
    building_id: str
    name: str
    floors: list[Floor] = field(default_factory=list)

    def add_floor(self, floor: Floor) -> None:
        for f in floor.facilities:
            f.building_id = self.building_id
        self.floors.append(floor)
        self.floors.sort(key=lambda fl: fl.level)

    def get_floor(self, level: int) -> Floor:
        for fl in self.floors:
            if fl.level == level:
                return fl
        raise KeyError(f"{self.name}에 {level}층 도면이 없습니다")

    def all_facilities(self) -> list[Facility]:
        return [fac for fl in self.floors for fac in fl.facilities]
