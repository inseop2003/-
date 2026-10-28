"""SearchService: 키워드 검색(초성 포함) + 카테고리 필터.

검색어와 시설 이름을 비교해 점수를 매기고, Min-Heap(heapq)으로
점수가 가장 좋은 항목부터 꺼낸다.  점수: 0 완전 일치 < 1 접두 일치 < 2 부분 일치 < 3 초성 일치
"""
from __future__ import annotations

import heapq
import re

from .domain import Category, Classroom, Facility

_CHO = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"


def to_chosung(text: str) -> str:
    out = []
    for ch in text:
        code = ord(ch) - 0xAC00
        out.append(_CHO[code // 588] if 0 <= code < 11172 else ch)
    return "".join(out)


def _norm(text: str) -> str:
    return re.sub(r"[\s\-_.]", "", text).lower()


def _is_chosung_only(text: str) -> bool:
    return bool(text) and all(ch in _CHO for ch in text)


class SearchService:
    def __init__(self, facilities: list[Facility]) -> None:
        self.facilities = list(facilities)
        # 미리 정규화해 둔 검색 키: (시설, [이름, 호실번호 ...])
        self._index = []
        for f in self.facilities:
            keys = [_norm(f.name)]
            if isinstance(f, Classroom):
                keys.append(_norm(f.get_room_number()))
            self._index.append((f, keys))

    @staticmethod
    def _score(query: str, key: str) -> int | None:
        if key == query:
            return 0
        if key.startswith(query):
            return 1
        if query in key:
            return 2
        if _is_chosung_only(query) and query in to_chosung(key):
            return 3
        return None

    def search(self, keyword: str, limit: int = 10) -> list[Facility]:
        q = _norm(keyword)
        if not q:
            return []
        heap: list[tuple[int, int, int, Facility]] = []
        for order, (fac, keys) in enumerate(self._index):
            scores = [s for k in keys if (s := self._score(q, k)) is not None]
            if scores:
                # (점수, 이름 길이, 입력 순서) → 짧고 정확한 이름이 먼저
                heapq.heappush(heap, (min(scores), len(fac.name), order, fac))
        return [heapq.heappop(heap)[3] for _ in range(min(limit, len(heap)))]

    def filter_by_category(self, category: Category, building_id: str | None = None,
                           floor: int | None = None) -> list[Facility]:
        return [f for f in self.facilities
                if f.category is category
                and (building_id is None or f.building_id == building_id)
                and (floor is None or f.floor_level == floor)]
