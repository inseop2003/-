"""동작 확인용 샘플 데이터.

※ 좌표·호실·연결 관계는 모두 임의 값입니다. 실제 도면 매핑이 끝나면
   이 파일 대신 SQLite DB(myongjimap.db)에 실제 데이터를 넣으세요.

5공학관 1F/2F 일부만 넣었다. 층간 이동은 계단(S1)과 엘리베이터(EV1) 두 가지.
계단이 더 가깝기 때문에 일반 경로는 계단으로, 배리어프리 경로는 엘리베이터로 간다.
"""

B = "ENG5"


def _n(nid, level, x, y, t="CORRIDOR"):
    return (nid, B, level, x, y, t)


SAMPLE = {
    "buildings": [(B, "5공학관"), ("HAMBAK", "함박관"), ("CHANGJO", "창조관")],
    "floors": [
        (B, 1, "/svg/eng5_1f.svg"),
        (B, 2, "/svg/eng5_2f.svg"),
        (B, 4, "/svg/eng5_4f.svg"),
    ],
    "nodes": [
        # 1층
        _n("1F_ENT", 1, 0, 50, "JUNCTION"),       # 정문
        _n("1F_C1", 1, 40, 50),
        _n("1F_C2", 1, 80, 50),
        _n("1F_S1", 1, 60, 70, "STAIRS"),
        _n("1F_EV1", 1, 120, 50, "ELEVATOR"),
        _n("1F_CAFE", 1, 40, 20),
        # 2층
        _n("2F_S1", 2, 60, 70, "STAIRS"),
        _n("2F_C1", 2, 60, 50),
        _n("2F_C2", 2, 100, 50),
        _n("2F_EV1", 2, 120, 50, "ELEVATOR"),
        _n("2F_201", 2, 60, 20),
        _n("2F_205", 2, 100, 20),
        _n("2F_PRN", 2, 120, 20),
    ],
    "edges": [
        ("1F_ENT", "1F_C1", 40, 1), ("1F_C1", "1F_C2", 40, 1), ("1F_C2", "1F_EV1", 40, 1),
        ("1F_C1", "1F_S1", 28, 1), ("1F_C1", "1F_CAFE", 30, 1),
        ("1F_S1", "2F_S1", 25, 1),        # 계단으로 한 층 이동
        ("1F_EV1", "2F_EV1", 30, 1),      # 엘리베이터로 한 층 이동(대기 시간 포함)
        ("2F_S1", "2F_C1", 20, 1), ("2F_C1", "2F_C2", 40, 1), ("2F_C2", "2F_EV1", 20, 1),
        ("2F_C1", "2F_201", 30, 1), ("2F_C2", "2F_205", 30, 1), ("2F_EV1", "2F_PRN", 30, 1),
    ],
    # facility_id, building, level, name, category, x, y, room_number, lab, outlet, node_id
    "facilities": [
        ("F_CAFE1", B, 1, "1층 카페", "CAFE", 40, 20, None, 0, 1, "1F_CAFE"),
        ("F_RR1", B, 1, "1층 화장실", "RESTROOM", 50, 75, None, 0, 0, "1F_S1"),
        ("F_EV1", B, 1, "엘리베이터", "ELEVATOR", 120, 50, None, 0, 0, "1F_EV1"),
        ("F_201", B, 2, "Y5201", "CLASSROOM", 60, 20, "Y5201", 1, 0, "2F_201"),
        ("F_205", B, 2, "Y5205", "CLASSROOM", 100, 20, "Y5205", 0, 0, "2F_205"),
        ("F_PRN2", B, 2, "2층 프린터", "PRINTER", 120, 20, None, 0, 0, "2F_PRN"),
        ("F_ST2", B, 2, "2층 자습공간", "STUDY_SPACE", 80, 60, None, 0, 1, "2F_C2"),
        ("F_OFF", B, 2, "컴퓨터공학과 사무실", "OFFICE", 70, 40, None, 0, 0, "2F_C1"),
    ],
}
