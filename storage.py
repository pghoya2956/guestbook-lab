"""리뷰 저장소. STORAGE 환경 변수로 file, mysql, dynamodb 중 하나를 고른다.

세 저장소는 같은 글 형식을 쓴다.
  id, ts(초), name(별명), msg(한줄평), image_key(S3 images/ 아래 사진 키),
  host(글을 받은 서버 이름), dish(어떤 메뉴에 대한 리뷰인지)
host 와 dish 는 급식 리뷰 앱에서 더한 필드다. 그 전에 쓴 글이나 서버리스 API(lambda/api)가 쓴 글에는
없을 수 있어서, 읽을 때 normalize 가 빈 값으로 채운다.
"""
import json
import os
import threading
import time
import uuid
from pathlib import Path

FIELDS = ("name", "msg", "image_key", "host", "dish")


def _new_item(entry):
    item = {"id": str(uuid.uuid4()), "ts": int(time.time())}
    for k in FIELDS:
        item[k] = entry.get(k) or ""
    return item


def normalize(item):
    """저장소에서 읽은 글 하나를 같은 모양으로 맞춘다. 없는 필드와 NULL 은 빈 문자열, ts 는 정수."""
    out = dict(item)
    out["id"] = str(out.get("id", ""))
    out["ts"] = int(out.get("ts") or 0)
    for k in FIELDS:
        v = out.get(k)
        out[k] = "" if v is None else str(v)
    if not out["name"]:
        out["name"] = "익명"
    return out


def _newest(items, limit):
    return sorted((normalize(i) for i in items), key=lambda x: x["ts"], reverse=True)[:limit]


class FileStore:
    """서버 디스크의 JSON 파일. 서버를 바꾸면 글이 사라진다(1학년 11단원에서 확인)."""

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
        return _newest(items, limit)

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
    # 방명록 때 만든 테이블에는 host, dish 칸이 없다. 앱이 켜질 때 없는 칸만 더한다
    ADDED_COLUMNS = {"host": "VARCHAR(100)", "dish": "VARCHAR(30)"}

    def __init__(self):
        import pymysql

        prefix = os.environ.get("PARAM_PREFIX", "/guestbook/db")
        self.conn_args = dict(
            host=_ssm_param(f"{prefix}/host"),
            port=int(os.environ.get("DB_PORT", "3306")),
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
                " msg VARCHAR(300), image_key VARCHAR(200), host VARCHAR(100), dish VARCHAR(30))"
            )
            cur.execute("SHOW COLUMNS FROM entries")
            have = {row["Field"] for row in cur.fetchall()}
            for col, kind in self.ADDED_COLUMNS.items():
                if col not in have:
                    cur.execute(f"ALTER TABLE entries ADD COLUMN {col} {kind}")
            c.commit()

    def _conn(self):
        return self.pymysql.connect(**self.conn_args)

    def list(self, limit=50):
        with self._conn() as c, c.cursor() as cur:
            cur.execute("SELECT * FROM entries ORDER BY ts DESC LIMIT %s", (limit,))
            return _newest(cur.fetchall(), limit)

    def add(self, entry):
        item = _new_item(entry)
        with self._conn() as c, c.cursor() as cur:
            cur.execute(
                "INSERT INTO entries (id, ts, name, msg, image_key, host, dish)"
                " VALUES (%(id)s, %(ts)s, %(name)s, %(msg)s, %(image_key)s, %(host)s, %(dish)s)",
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
        return _newest(items, limit)

    def add(self, entry):
        self.table.put_item(Item=_new_item(entry))


def from_env():
    kind = os.environ.get("STORAGE", "file")
    if kind == "mysql":
        return MySQLStore()
    if kind == "dynamodb":
        return DynamoStore()
    return FileStore(os.environ.get("DATA_FILE", "data/entries.json"))
