"""RouteFinder: 우선순위 큐(Min-Heap) 기반 Dijkstra, O((V+E) log V)."""
from __future__ import annotations

import heapq
from dataclasses import dataclass

from .graph import Graph, Node


class NoRouteError(Exception):
    pass


@dataclass
class Route:
    nodes: list[Node]
    distance: float
    barrier_free: bool

    @property
    def floor_changes(self) -> list[dict]:
        """층이 바뀌는 지점 (계단/엘리베이터 안내 인디케이터용)."""
        out = []
        for a, b in zip(self.nodes, self.nodes[1:]):
            if a.floor != b.floor or a.building_id != b.building_id:
                out.append({"at": a.node_id, "via": a.type.value,
                            "fromFloor": a.floor, "toFloor": b.floor})
        return out

    def to_dict(self) -> dict:
        return {"distance": round(self.distance, 2), "barrierFree": self.barrier_free,
                "path": [n.to_dict() for n in self.nodes], "floorChanges": self.floor_changes}


class RouteFinder:
    def __init__(self, graph: Graph) -> None:
        self.graph = graph
        self._bf_graph: Graph | None = None   # 계단 제외 그래프 캐시

    def find_shortest_path(self, start: str, end: str) -> Route:
        return self._dijkstra(self.graph, start, end, barrier_free=False)

    def find_barrier_free_path(self, start: str, end: str) -> Route:
        if self._bf_graph is None:
            self._bf_graph = self.graph.exclude_stairs()
        for nid in (start, end):
            if nid in self.graph.nodes and self.graph.nodes[nid].is_stairs():
                raise NoRouteError(f"출발/도착지가 계단 노드입니다: {nid}")
        return self._dijkstra(self._bf_graph, start, end, barrier_free=True)

    @staticmethod
    def _dijkstra(g: Graph, start: str, end: str, barrier_free: bool) -> Route:
        if start not in g.nodes or end not in g.nodes:
            raise NoRouteError(f"그래프에 없는 노드: {start if start not in g.nodes else end}")
        dist: dict[str, float] = {start: 0.0}
        prev: dict[str, str] = {}
        heap: list[tuple[float, str]] = [(0.0, start)]
        done: set[str] = set()
        while heap:
            d, u = heapq.heappop(heap)
            if u in done:
                continue                       # 이미 확정된 노드의 낡은 항목
            if u == end:
                break
            done.add(u)
            for e in g.get_neighbors(u):
                nd = d + e.get_weight()
                if nd < dist.get(e.target, float("inf")):
                    dist[e.target] = nd
                    prev[e.target] = u
                    heapq.heappush(heap, (nd, e.target))
        if end not in dist:
            kind = "계단 없는 경로" if barrier_free else "경로"
            raise NoRouteError(f"{start} → {end} {kind}를 찾을 수 없습니다")
        path = [end]
        while path[-1] != start:
            path.append(prev[path[-1]])
        path.reverse()
        return Route([g.nodes[n] for n in path], dist[end], barrier_free)
