"""SQLite 저장소.

- 지도 데이터(건물/층/시설/노드/간선): 시작할 때 한 번 읽어 도메인 객체로 만든다 (읽기 전용).
- 사용자 데이터(즐겨찾기, 지름길 게시판): 요청마다 읽고 쓴다.
"""
from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from .domain import Amenity, Building, Category, Classroom, Floor, Point
from .graph import Graph, Node, NodeType

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS building (
    building_id TEXT PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS floor (
    building_id TEXT REFERENCES building, level INTEGER, svg_url TEXT,
    PRIMARY KEY (building_id, level));
CREATE TABLE IF NOT EXISTS facility (
    facility_id TEXT PRIMARY KEY, building_id TEXT, level INTEGER,
    name TEXT NOT NULL, category TEXT NOT NULL, x REAL, y REAL,
    room_number TEXT, has_computer_lab INTEGER DEFAULT 0, has_outlet INTEGER DEFAULT 0,
    node_id TEXT);
CREATE TABLE IF NOT EXISTS node (
    node_id TEXT PRIMARY KEY, building_id TEXT, level INTEGER, x REAL, y REAL, type TEXT);
CREATE TABLE IF NOT EXISTS edge (
    source TEXT REFERENCES node, target TEXT REFERENCES node, weight REAL,
    bidirectional INTEGER DEFAULT 1);

-- 사용자 데이터 (user_id = 프론트엔드가 만든 익명 기기 ID)
CREATE TABLE IF NOT EXISTS favorite (
    user_id TEXT NOT NULL, facility_id TEXT NOT NULL REFERENCES facility,
    created_at TEXT NOT NULL, PRIMARY KEY (user_id, facility_id));
CREATE TABLE IF NOT EXISTS shortcut (
    shortcut_id INTEGER PRIMARY KEY AUTOINCREMENT,
    author_id TEXT NOT NULL, building_id TEXT NOT NULL REFERENCES building,
    from_facility_id TEXT REFERENCES facility, to_facility_id TEXT REFERENCES facility,
    title TEXT NOT NULL, body TEXT NOT NULL, created_at TEXT NOT NULL,
    like_count INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS shortcut_like (
    shortcut_id INTEGER NOT NULL REFERENCES shortcut ON DELETE CASCADE,
    user_id TEXT NOT NULL, PRIMARY KEY (shortcut_id, user_id));
CREATE INDEX IF NOT EXISTS ix_shortcut_building ON shortcut(building_id, created_at);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Repository:
    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self._lock = threading.Lock()      # FastAPI 동기 엔드포인트는 스레드풀에서 돈다

    # ================= 지도 데이터 =================
    def is_empty(self) -> bool:
        return self.conn.execute("SELECT COUNT(*) FROM building").fetchone()[0] == 0

    def seed(self, data: dict) -> None:
        with self._lock, self.conn as c:
            c.executemany("INSERT INTO building VALUES (?,?)", data["buildings"])
            c.executemany("INSERT INTO floor VALUES (?,?,?)", data["floors"])
            c.executemany("""INSERT INTO facility (facility_id, building_id, level, name, category, x, y,
                             room_number, has_computer_lab, has_outlet, node_id)
                             VALUES (?,?,?,?,?,?,?,?,?,?,?)""", data["facilities"])
            c.executemany("INSERT INTO node VALUES (?,?,?,?,?,?)", data["nodes"])
            c.executemany("INSERT INTO edge VALUES (?,?,?,?)", data["edges"])

    def reseed_map(self, data: dict) -> None:
        """도면 데이터만 새로 넣는다 (사용자 데이터는 그대로). 도면을 고친 뒤 실행."""
        with self._lock, self.conn as c:
            c.execute("PRAGMA foreign_keys = OFF")
            for t in ("edge", "node", "facility", "floor", "building"):
                c.execute(f"DELETE FROM {t}")
        self.seed(data)
        self.conn.execute("PRAGMA foreign_keys = ON")

    def load_buildings(self) -> dict[str, Building]:
        buildings = {r["building_id"]: Building(r["building_id"], r["name"])
                     for r in self.conn.execute("SELECT * FROM building")}
        floors: dict[tuple[str, int], Floor] = {}
        for r in self.conn.execute("SELECT * FROM floor"):
            floors[(r["building_id"], r["level"])] = Floor(r["level"], r["svg_url"])
        for r in self.conn.execute("SELECT * FROM facility"):
            cat = Category(r["category"])
            loc = Point(r["x"], r["y"])
            if cat is Category.CLASSROOM:
                fac = Classroom(r["facility_id"], r["name"], loc, r["room_number"] or r["name"],
                                bool(r["has_computer_lab"]), r["node_id"])
            else:
                fac = Amenity(r["facility_id"], r["name"], loc, cat, bool(r["has_outlet"]), r["node_id"])
            floors[(r["building_id"], r["level"])].add_facility(fac)
        for (bid, _), fl in floors.items():
            buildings[bid].add_floor(fl)
        return buildings

    def load_graph(self) -> Graph:
        g = Graph()
        for r in self.conn.execute("SELECT * FROM node"):
            g.add_node(Node(r["node_id"], r["building_id"], r["level"],
                            Point(r["x"], r["y"]), NodeType(r["type"])))
        for r in self.conn.execute("SELECT * FROM edge"):
            g.add_edge(r["source"], r["target"], r["weight"], bool(r["bidirectional"]))
        return g

    # ================= 즐겨찾기 =================
    def list_favorites(self, user_id: str) -> list[str]:
        rows = self.conn.execute(
            "SELECT facility_id FROM favorite WHERE user_id=? ORDER BY created_at, rowid", (user_id,))
        return [r[0] for r in rows]

    def add_favorite(self, user_id: str, facility_id: str) -> bool:
        """새로 추가했으면 True, 이미 있었으면 False."""
        with self._lock, self.conn as c:
            cur = c.execute("INSERT OR IGNORE INTO favorite VALUES (?,?,?)", (user_id, facility_id, _now()))
            return cur.rowcount == 1

    def remove_favorite(self, user_id: str, facility_id: str) -> bool:
        with self._lock, self.conn as c:
            cur = c.execute("DELETE FROM favorite WHERE user_id=? AND facility_id=?", (user_id, facility_id))
            return cur.rowcount == 1

    # ================= 지름길 게시판 =================
    def create_shortcut(self, author_id: str, building_id: str, title: str, body: str,
                        from_facility_id: str | None, to_facility_id: str | None) -> int:
        with self._lock, self.conn as c:
            cur = c.execute(
                """INSERT INTO shortcut (author_id, building_id, from_facility_id, to_facility_id,
                   title, body, created_at) VALUES (?,?,?,?,?,?,?)""",
                (author_id, building_id, from_facility_id, to_facility_id, title, body, _now()))
            return cur.lastrowid

    def get_shortcut(self, shortcut_id: int) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM shortcut WHERE shortcut_id=?", (shortcut_id,)).fetchone()

    def list_shortcuts(self, building_id: str | None, sort: str, limit: int, offset: int
                       ) -> tuple[list[sqlite3.Row], int]:
        where, args = ("WHERE building_id=?", [building_id]) if building_id else ("", [])
        order = "like_count DESC, shortcut_id DESC" if sort == "popular" else "shortcut_id DESC"
        total = self.conn.execute(f"SELECT COUNT(*) FROM shortcut {where}", args).fetchone()[0]
        rows = self.conn.execute(f"SELECT * FROM shortcut {where} ORDER BY {order} LIMIT ? OFFSET ?",
                                 [*args, limit, offset]).fetchall()
        return rows, total

    def delete_shortcut(self, shortcut_id: int) -> None:
        with self._lock, self.conn as c:
            c.execute("DELETE FROM shortcut WHERE shortcut_id=?", (shortcut_id,))

    def liked_by(self, shortcut_ids: list[int], user_id: str | None) -> set[int]:
        if not user_id or not shortcut_ids:
            return set()
        q = ",".join("?" * len(shortcut_ids))
        rows = self.conn.execute(
            f"SELECT shortcut_id FROM shortcut_like WHERE user_id=? AND shortcut_id IN ({q})",
            [user_id, *shortcut_ids])
        return {r[0] for r in rows}

    def toggle_like(self, shortcut_id: int, user_id: str) -> tuple[bool, int]:
        """좋아요를 켜거나 끈다 → (지금 좋아요 상태, 좋아요 수)."""
        with self._lock, self.conn as c:
            if c.execute("DELETE FROM shortcut_like WHERE shortcut_id=? AND user_id=?",
                         (shortcut_id, user_id)).rowcount:
                liked, delta = False, -1
            else:
                c.execute("INSERT INTO shortcut_like VALUES (?,?)", (shortcut_id, user_id))
                liked, delta = True, 1
            c.execute("UPDATE shortcut SET like_count = like_count + ? WHERE shortcut_id=?",
                      (delta, shortcut_id))
            count = c.execute("SELECT like_count FROM shortcut WHERE shortcut_id=?",
                              (shortcut_id,)).fetchone()[0]
        return liked, count
