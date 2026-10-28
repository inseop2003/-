"""서비스 구역 전체 데이터 = 5공학관 + 창조관 + 함박관."""
from .changjo_data import CHANGJO
from .eng5_data import ENG5
from .hambak_data import HAMBAK

_PARTS = (ENG5, CHANGJO, HAMBAK)
CAMPUS = {
    "buildings": ENG5["buildings"],
    **{k: [row for part in _PARTS for row in part[k]] for k in ("floors", "nodes", "edges", "facilities")},
}
