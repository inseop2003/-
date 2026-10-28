"""길찾기 그래프 G = (V, E) (보고서 II-4)

노드 V: 강의실 앞·복도 분기점·계단·엘리베이터·경사로
간선 E: 노드를 잇는 복도/통로, 가중치 = 거리(또는 이동 시간)
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .domain import Point


class NodeType(str, Enum):
    CORRIDOR = "CORRIDOR"
    STAIRS = "STAIRS"
    ELEVATOR = "ELEVATOR"
    RAMP = "RAMP"
    JUNCTION = "JUNCTION"
    ENTRANCE = "ENTRANCE"      # 건물 출입구 (건물 간 길찾기의 연결점)


@dataclass(frozen=True)
class Node:
    node_id: str
    building_id: str
    floor: int
    location: Point
    type: NodeType = NodeType.CORRIDOR

    def is_stairs(self) -> bool:
        return self.type is NodeType.STAIRS

    def is_entrance(self) -> bool:
        return self.type is NodeType.ENTRANCE

    def to_dict(self) -> dict:
        return {"nodeId": self.node_id, "buildingId": self.building_id, "floor": self.floor,
                "x": self.location.x, "y": self.location.y, "type": self.type.value}


@dataclass(frozen=True)
class Edge:
    source: str        # 다이어그램의 from (파이썬 예약어라 이름 변경)
    target: str        # 다이어그램의 to
    weight: float

    def get_weight(self) -> float:
        return self.weight


class Graph:
    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}
        self.adj_list: dict[str, list[Edge]] = {}

    # ---- 구성 ----
    def add_node(self, node: Node) -> None:
        if node.node_id in self.nodes:
            raise ValueError(f"중복 노드: {node.node_id}")
        self.nodes[node.node_id] = node
        self.adj_list.setdefault(node.node_id, [])

    def add_edge(self, a: str, b: str, weight: float | None = None,
                 bidirectional: bool = True) -> None:
        """weight를 생략하면 같은 층 두 노드의 평면 거리를 가중치로 쓴다."""
        for nid in (a, b):
            if nid not in self.nodes:
                raise KeyError(f"없는 노드: {nid}")
        if weight is None:
            na, nb = self.nodes[a], self.nodes[b]
            if na.floor != nb.floor or na.building_id != nb.building_id:
                raise ValueError("층/건물이 다른 간선은 weight를 직접 지정해야 합니다")
            weight = na.location.distance_to(nb.location)
        if weight < 0:
            raise ValueError("Dijkstra는 음수 가중치를 허용하지 않습니다")
        self.adj_list[a].append(Edge(a, b, weight))
        if bidirectional:
            self.adj_list[b].append(Edge(b, a, weight))

    # ---- 조회 ----
    def get_neighbors(self, node_id: str) -> list[Edge]:
        return self.adj_list.get(node_id, [])

    def exclude_stairs(self) -> "Graph":
        """계단 노드와 그에 닿은 간선을 뺀 부분 그래프 (배리어프리 탐색용)."""
        g = Graph()
        for n in self.nodes.values():
            if not n.is_stairs():
                g.add_node(n)
        for src, edges in self.adj_list.items():
            if src not in g.nodes:
                continue
            g.adj_list[src] = [e for e in edges if e.target in g.nodes]
        return g

    def __len__(self) -> int:
        return len(self.nodes)
