"""CampusService: 건물·그래프·검색·길찾기를 한데 묶은 서비스 계층.

API(라우터)는 이 클래스만 보고, 도메인 객체와 알고리즘은 이 뒤에 숨긴다.
건물 간 길찾기도 여기서 처리한다:
  출발 건물 안 경로 → 출입구 → (실외 이동) → 도착 건물 출입구 → 도착 건물 안 경로
실외 구간은 아직 지도 데이터가 없어 거리를 모르므로, 두 건물 안 거리 합이 가장 작은
출입구 쌍을 고르고 실외 구간은 OUTDOOR 단계로만 안내한다.
"""
from __future__ import annotations

from .config import Settings
from .directions import build_steps, floor_label, node_label, ro
from .domain import Building, Category, Facility, Point
from .graph import Graph, Node
from .route_finder import NoRouteError, Route, RouteFinder
from .search_service import SearchService


class NotFound(Exception):
    """요청한 건물/층/시설/노드가 없음 → 404."""


class CampusService:
    def __init__(self, buildings: dict[str, Building], graph: Graph, settings: Settings) -> None:
        self.buildings = buildings
        self.graph = graph
        self.settings = settings
        self.facilities: list[Facility] = [f for b in buildings.values() for f in b.all_facilities()]
        self.facility_by_id = {f.facility_id: f for f in self.facilities}
        self.search_service = SearchService(self.facilities)
        self.route_finder = RouteFinder(graph)
        self.building_names = {b.building_id: b.name for b in buildings.values()}

    # ---------------- 조회 ----------------
    def building(self, building_id: str) -> Building:
        try:
            return self.buildings[building_id]
        except KeyError:
            raise NotFound(f"건물이 없습니다: {building_id}") from None

    def facility(self, facility_id: str) -> Facility:
        try:
            return self.facility_by_id[facility_id]
        except KeyError:
            raise NotFound(f"시설이 없습니다: {facility_id}") from None

    def facilities_where(self, category: Category | None, building_id: str | None,
                         floor: int | None) -> list[Facility]:
        if category is not None:
            return self.search_service.filter_by_category(category, building_id, floor)
        return [f for f in self.facilities
                if (building_id is None or f.building_id == building_id)
                and (floor is None or f.floor_level == floor)]

    def floor_nodes(self, building_id: str, level: int) -> list[Node]:
        self.building(building_id).get_floor(level)          # 없으면 KeyError
        return [n for n in self.graph.nodes.values() if n.building_id == building_id and n.floor == level]

    def nearest_node(self, building_id: str, level: int, x: float, y: float,
                     barrier_free: bool = False) -> Node:
        """지도에서 찍은 위치와 가장 가까운 노드 ('내 위치' 지정용). 계단 노드는 빼고 고른다."""
        p = Point(x, y)
        cands = [n for n in self.floor_nodes(building_id, level) if not n.is_stairs()]
        if not cands:
            raise NotFound("이 층에는 길찾기 노드가 없습니다")
        return min(cands, key=lambda n: n.location.distance_to(p))

    # ---------------- 길찾기 ----------------
    def resolve_node(self, ref: str) -> Node:
        """시설 ID 또는 노드 ID → 노드."""
        if ref in self.facility_by_id:
            nid = self.facility_by_id[ref].node_id
            if nid is None:
                raise NoRouteError(f"{ref}는 길찾기 노드와 연결되어 있지 않습니다")
            ref = nid
        if ref not in self.graph.nodes:
            raise NotFound(f"시설이나 노드가 없습니다: {ref}")
        return self.graph.nodes[ref]

    def _find(self, a: str, b: str, barrier_free: bool) -> Route:
        rf = self.route_finder
        return rf.find_barrier_free_path(a, b) if barrier_free else rf.find_shortest_path(a, b)

    def _entrances(self, building_id: str) -> list[Node]:
        return [n for n in self.graph.nodes.values() if n.building_id == building_id and n.is_entrance()]

    def _meters(self, building_id: str, units: float) -> float | None:
        mpu = self.settings.meters_per_unit.get(building_id)
        return None if mpu is None else round(units * mpu, 1)

    def _indoor_leg(self, r: Route) -> dict:
        bid = r.nodes[0].building_id
        return {"kind": "INDOOR", "buildingId": bid, "distance": round(r.distance, 2),
                "distanceMeters": self._meters(bid, r.distance),
                "path": [n.to_dict() for n in r.nodes], "floorChanges": r.floor_changes,
                "steps": build_steps(r.nodes, self.building_names)}

    def route(self, start: str, end: str, barrier_free: bool = False) -> dict:
        s, d = self.resolve_node(start), self.resolve_node(end)
        if s.building_id == d.building_id:
            legs = [self._indoor_leg(self._find(s.node_id, d.node_id, barrier_free))]
        else:
            legs = self._cross_building(s, d, barrier_free)

        indoor = [leg for leg in legs if leg["kind"] == "INDOOR"]
        meters = [leg["distanceMeters"] for leg in indoor]
        total_m = None if any(m is None for m in meters) else round(sum(meters), 1)
        steps = []
        for leg in legs:
            steps.extend(leg["steps"])
        return {
            "barrierFree": barrier_free,
            "crossBuilding": len(legs) > 1,
            "distance": round(sum(leg["distance"] for leg in indoor), 2),   # 실내 구간 합 (도면 단위)
            "distanceMeters": total_m,
            "etaSeconds": None if total_m is None else round(total_m / self.settings.walking_speed_mps),
            "legs": legs,
            # 아래 세 필드는 예전 클라이언트 호환용 (실내 경로 노드를 이어 붙인 것)
            "path": [p for leg in indoor for p in leg["path"]],
            "floorChanges": [c for leg in indoor for c in leg["floorChanges"]],
            "steps": steps,
        }

    def _cross_building(self, s: Node, d: Node, barrier_free: bool) -> list[dict]:
        exits, entries = self._entrances(s.building_id), self._entrances(d.building_id)
        if not exits or not entries:
            raise NoRouteError("출입구 정보가 없어 건물 간 경로를 만들 수 없습니다")
        out_legs = {}
        for e in exits:
            try:
                out_legs[e.node_id] = self._find(s.node_id, e.node_id, barrier_free)
            except NoRouteError:
                pass
        in_legs = {}
        for e in entries:
            try:
                in_legs[e.node_id] = self._find(e.node_id, d.node_id, barrier_free)
            except NoRouteError:
                pass
        if not out_legs or not in_legs:
            kind = "계단 없이 나갈" if barrier_free else "나갈"
            raise NoRouteError(f"{kind} 수 있는 출입구가 없습니다")
        out_r = min(out_legs.values(), key=lambda r: r.distance)
        in_r = min(in_legs.values(), key=lambda r: r.distance)
        a, b = out_r.nodes[-1], in_r.nodes[0]
        an, bn = self.building_names[a.building_id], self.building_names[b.building_id]
        outdoor = {
            "kind": "OUTDOOR", "fromNodeId": a.node_id, "toNodeId": b.node_id,
            "fromBuildingId": a.building_id, "toBuildingId": b.building_id,
            "distance": None, "distanceMeters": None,
            "steps": [{"type": "OUTDOOR", "nodeId": b.node_id, "floor": b.floor,
                       "text": f"{an} {ro(node_label(a))} 나가 {bn} {node_label(b)}까지 실외 이동"}],
        }
        first, last = self._indoor_leg(out_r), self._indoor_leg(in_r)
        # 첫 구간의 '도착'은 '건물 밖으로', 둘째 구간의 '출발'은 '건물 안으로'로 바꾼다
        first["steps"][-1] = {"type": "EXIT", "nodeId": a.node_id, "floor": a.floor,
                              "text": f"{node_label(a)}에서 {an} 밖으로 나가기"}
        last["steps"][0] = {"type": "ENTER", "nodeId": b.node_id, "floor": b.floor,
                            "text": f"{bn} {floor_label(b.floor)}층 {ro(node_label(b))} 들어가기"}
        return [first, outdoor, last]
