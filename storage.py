"""방명록 저장소. STORAGE 환경 변수로 file, mysql, dynamodb 중 하나를 고른다."""
import json
import os
import threading
import time
import uuid
from pathlib import Path


def _new_item(entry):
    return {
        "id": str(uuid.uuid4()),
        "ts": int(time.time()),
        "name": entry["name"],
        "msg": entry["msg"],
        "image_key": entry.get("image_key", ""),
    }


class FileStore:
    """서버 디스크의 JSON 파일. 서버를 바꾸면 글이 사라진다(13단원에서 확인)."""

    name = "file"

    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.Lock()

    def _read(self):
        if not self.path.exists():
            return []
        return json.loads(self.path.read_text(encoding="utf-8"))

    def list(self, limit=50):
        with self.lock:
            items = self._read()
        return sorted(items, key=lambda x: x["ts"], reverse=True)[:limit]

    def add(self, entry):
        with self.lock:
            items = self._read()
            items.append(_new_item(entry))
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")


def _ssm_param(name, decrypt=False):
    import boto3

    ssm = boto3.client("ssm", region_name=os.environ.get("AWS_REGION", "ap-northeast-2"))
    return ssm.get_parameter(Name=name, WithDecryption=decrypt)["Parameter"]["Value"]


class MySQLStore:
    """RDS MySQL. 접속 정보는 Parameter Store 에서 읽는다(2학년 4단원)."""

    name = "mysql"

    def __init__(self):
        import pymysql

        prefix = os.environ.get("PARAM_PREFIX", "/guestbook/db")
        self.conn_args = dict(
            host=_ssm_param(f"{prefix}/host"),
            user=os.environ.get("DB_USER", "admin"),
            password=_ssm_param(f"{prefix}/password", decrypt=True),
            database=os.environ.get("DB_NAME", "guestbook"),
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=5,
        )
        self.pymysql = pymysql
        with self._conn() as c, c.cursor() as cur:
            cur.execute(
                "CREATE TABLE IF NOT EXISTS entries ("
                " id VARCHAR(36) PRIMARY KEY, ts BIGINT, name VARCHAR(30),"
                " msg VARCHAR(300), image_key VARCHAR(200))"
            )
            c.commit()

    def _conn(self):
        return self.pymysql.connect(**self.conn_args)

    def list(self, limit=50):
        with self._conn() as c, c.cursor() as cur:
            cur.execute("SELECT * FROM entries ORDER BY ts DESC LIMIT %s", (limit,))
            return list(cur.fetchall())

    def add(self, entry):
        item = _new_item(entry)
        with self._conn() as c, c.cursor() as cur:
            cur.execute(
                "INSERT INTO entries (id, ts, name, msg, image_key)"
                " VALUES (%(id)s, %(ts)s, %(name)s, %(msg)s, %(image_key)s)",
                item,
            )
            c.commit()


class DynamoStore:
    """DynamoDB 테이블(파티션 키 id). 미니 프로젝트 메뉴와 2학년 11단원."""

    name = "dynamodb"

    def __init__(self):
        import boto3

        region = os.environ.get("AWS_REGION", "ap-northeast-2")
        table = os.environ.get("DYNAMODB_TABLE", "guestbook")
        self.table = boto3.resource("dynamodb", region_name=region).Table(table)

    def list(self, limit=50):
        items = self.table.scan(Limit=200).get("Items", [])
        for i in items:
            i["ts"] = int(i.get("ts", 0))
        return sorted(items, key=lambda x: x["ts"], reverse=True)[:limit]

    def add(self, entry):
        self.table.put_item(Item=_new_item(entry))


def from_env():
    kind = os.environ.get("STORAGE", "file")
    if kind == "mysql":
        return MySQLStore()
    if kind == "dynamodb":
        return DynamoStore()
    return FileStore(os.environ.get("DATA_FILE", "data/entries.json"))
