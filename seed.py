"""도면 데이터를 SQLite 파일에 넣는다 (사용자 데이터는 지우지 않음).

    python -m app.seed myongjimap.db

도면(tools/build_*.py)을 다시 생성한 뒤 실행하고 서버를 재시작하면 반영된다.
"""
import sys

from .campus_data import CAMPUS
from .repository import Repository


def main(path: str) -> None:
    repo = Repository(path)
    repo.reseed_map(CAMPUS)
    n = repo.conn.execute("SELECT COUNT(*) FROM facility").fetchone()[0]
    print(f"{path}: 시설 {n}곳, 노드 {len(CAMPUS['nodes'])}개, 간선 {len(CAMPUS['edges'])}개")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "myongjimap.db")
