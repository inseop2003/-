"""경로(노드 목록)를 사람이 읽는 단계별 안내 문장으로 바꾼다.

예) 3층 남쪽 출입구 → 지하 1층 9010
  1. 함박관 3층 출입구(남)에서 출발
  2. 3층 복도를 따라 계단A까지 이동
  3. 계단A 이용해 B1층으로 이동
  4. B1층 복도를 따라 9010으로 이동 · 도착
"""
from __future__ import annotations

import re

from .graph import Node, NodeType

_PREFIX = re.compile(r"^(CJ|HB)?B?\d+F_")
_BUILDING_NAMES = {"ENG5": "5공학관", "CHANGJO": "창조관", "HAMBAK": "함박관"}


def node_label(node: Node) -> str:
    """'HBB1F_9010' → '9010', 'CJ4F_EV(동)' → '엘리베이터(동)'."""
    label = _PREFIX.sub("", node.node_id)
    if node.type is NodeType.ELEVATOR:
        label = label.replace("EV", "엘리베이터")
    return label


def floor_label(level: int) -> str:
    return f"B{-level}" if level < 0 else str(level)


# 받침 유무로 조사 고르기. 숫자는 읽는 소리 기준(0 영, 1 일 …).
_DIGIT_BATCHIM = {"0": "o", "1": "l", "2": "", "3": "o", "4": "", "5": "", "6": "o",
                  "7": "l", "8": "l", "9": ""}


def _batchim(word: str) -> str | None:
    """'' = 받침 없음, 'l' = ㄹ 받침, 'o' = 그 밖의 받침, None = 판단 불가."""
    w = re.sub(r"\([^)]*\)$", "", word).strip() or word
    ch = w[-1]
    if "가" <= ch <= "힣":
        jong = (ord(ch) - 0xAC00) % 28
        return "" if jong == 0 else ("l" if jong == 8 else "o")
    return _DIGIT_BATCHIM.get(ch)


def ro(word: str) -> str:
    """word + (으)로."""
    b = _batchim(word)
    return word + ("(으)로" if b is None else "으로" if b == "o" else "로")


def eseo(word: str) -> str:
    return word + "에서"


def build_steps(nodes: list[Node], building_names: dict[str, str] | None = None) -> list[dict]:
    """한 건물 안 경로 → 안내 단계 목록."""
    names = building_names or _BUILDING_NAMES
    if not nodes:
        return []
    first, last = nodes[0], nodes[-1]
    steps = [{"type": "START", "nodeId": first.node_id, "floor": first.floor,
              "text": eseo(f"{names.get(first.building_id, first.building_id)} "
                           f"{floor_label(first.floor)}층 {node_label(first)}") + " 출발"}]
    if len(nodes) == 1:
        steps.append({"type": "ARRIVE", "nodeId": last.node_id, "floor": last.floor, "text": "도착"})
        return steps

    i = 0
    while i < len(nodes) - 1:
        a, b = nodes[i], nodes[i + 1]
        if a.floor != b.floor:
            # 같은 계단/엘리베이터로 여러 층을 연속 이동하면 한 단계로 합친다
            j = i + 1
            while j < len(nodes) - 1 and nodes[j].floor != nodes[j + 1].floor:
                j += 1
            how = node_label(a)
            steps.append({"type": "FLOOR_CHANGE", "nodeId": a.node_id, "floor": nodes[j].floor,
                          "via": a.type.value,
                          "text": f"{how} 이용해 {floor_label(nodes[j].floor)}층으로 이동"})
            i = j
            continue
        # 같은 층 구간: 다음 층 이동 지점(또는 도착지)까지 묶는다
        j = i + 1
        while j < len(nodes) - 1 and nodes[j].floor == nodes[j + 1].floor:
            j += 1
        target = nodes[j]
        is_end = j == len(nodes) - 1
        text = f"{floor_label(a.floor)}층 복도를 따라 {ro(node_label(target))} 이동"
        if not is_end:
            text = f"{floor_label(a.floor)}층 복도를 따라 {node_label(target)}까지 이동"
        steps.append({"type": "WALK", "nodeId": target.node_id, "floor": a.floor, "text": text})
        i = j
    steps.append({"type": "ARRIVE", "nodeId": last.node_id, "floor": last.floor,
                  "text": f"{node_label(last)} 도착"})
    return steps
