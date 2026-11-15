"""영향도 검사 반영(2026-11-15): 리뷰에 그 시점 메뉴 원문, 지난 날 식판, 옛 코드 서버와 같은 저장소, 설정 견본 순서,
5MB 넘는 사진, notice.txt BOM 과 주석, 문구, 판 번호."""
import importlib
import importlib.util
import io
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from moto import mock_aws

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

KST = timezone(timedelta(hours=9))
MENU = "밥|현미밥|\n국|소고기미역국|5.6.16\n반찬|닭갈비|5.6.13.15\n반찬|콩나물무침|5.6\n반찬|배추김치|9.13\n후식|귤|\n열량|812"
OLD_MENU = "밥|카레라이스|5.6\n국|맑은국|\n반찬|돈가스|1.5.6\n반찬|단무지|\n반찬|깍두기|9.13"
OLD_COMMIT = "308f72b"  # 급식 앱 첫 판. 수업 중 이 판과 새 판 서버가 한 저장소를 같이 쓸 수 있다


def _load(monkeypatch, tmp_path, **env):
    base = {"STORAGE": "file", "DATA_FILE": str(tmp_path / "entries.json"), "NOTICE_BUCKET": "", "IMAGE_BUCKET": "",
            "HELLO_API_URL": "", "TARGET_GROUP_ARN": ""}
    base.update(env)
    for k, v in base.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("AWS_DEFAULT_REGION", "ap-northeast-2")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    for k in ("AWS_PROFILE", "AWS_ENDPOINT_URL", "AWS_ENDPOINT_URL_S3"):
        monkeypatch.delenv(k, raising=False)
    for m in ("app", "storage"):
        sys.modules.pop(m, None)
    return importlib.import_module("app")


def _bucket(name, body=None, raw=None):
    import boto3

    s3 = boto3.client("s3", region_name="ap-northeast-2")
    s3.create_bucket(Bucket=name, CreateBucketConfiguration={"LocationConstraint": "ap-northeast-2"})
    if body is not None or raw is not None:
        s3.put_object(Bucket=name, Key="notice.txt", Body=raw if raw is not None else body.encode())
    return s3


def _ts(d, hour=12, minute=0):
    return int(datetime(d.year, d.month, d.day, hour, minute, tzinfo=KST).timestamp())


def _review(d, name, msg, dish="", image_key="", menu=None, hour=12):
    r = {"id": f"{name}-{d}-{hour}", "ts": _ts(d, hour), "name": name, "msg": msg, "image_key": image_key,
         "host": "ip-10-0-1-24", "dish": dish}
    if menu is not None:
        r["menu"] = menu
    return r


def _tray(body):
    return body.split('id="menu"')[1].split("</section>")[0]


def _old_storage(tmp_path):
    """308f72b 의 storage.py(리뷰에 menu 칸이 없는 옛 판)를 따로 읽는다."""
    src = subprocess.run(["git", "-C", str(ROOT), "show", f"{OLD_COMMIT}:storage.py"], capture_output=True, text=True, check=True).stdout
    p = tmp_path / "old_storage.py"
    p.write_text(src, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("old_storage", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --- 리뷰에 그 시점 메뉴 원문을 남긴다 ---

@mock_aws
def test_review_keeps_notice_text_at_that_moment(monkeypatch, tmp_path):
    s3 = _bucket("notice-test", MENU)
    app = _load(monkeypatch, tmp_path, NOTICE_BUCKET="notice-test")
    c = app.app.test_client()
    c.post("/entries", data={"name": "a", "msg": "첫 리뷰", "dish": "닭갈비"})
    s3.put_object(Bucket="notice-test", Key="notice.txt", Body=OLD_MENU.encode())
    c.post("/entries", data={"name": "b", "msg": "둘째 리뷰"})
    saved = json.loads((tmp_path / "entries.json").read_text(encoding="utf-8"))
    assert [e["menu"] for e in saved] == [MENU, OLD_MENU]
    assert not (tmp_path / "menus.json").exists()  # 별도 메뉴 파일은 없다


def test_review_without_notice_bucket_has_empty_menu(monkeypatch, tmp_path):
    app = _load(monkeypatch, tmp_path)
    app.app.test_client().post("/entries", data={"name": "a", "msg": "b"})
    assert json.loads((tmp_path / "entries.json").read_text(encoding="utf-8"))[0]["menu"] == ""


# --- 지난 날 식판 ---

def test_past_day_tray_from_latest_review_menu_with_that_days_photos(monkeypatch, tmp_path):
    app = _load(monkeypatch, tmp_path, IMAGE_BUCKET="img-test")
    monkeypatch.setattr(app, "image_url", lambda k: f"https://img.example/{k}" if k else "")
    today = app.today_kst()
    yday, two = today - timedelta(days=1), today - timedelta(days=2)
    (tmp_path / "entries.json").write_text(json.dumps([
        _review(yday, "a", "아침 메뉴로 쓴 리뷰", "돈가스", menu=MENU, hour=9),
        _review(yday, "b", "돈가스 바삭", "돈가스", "images/yday-donkatsu.jpg", menu=OLD_MENU, hour=12),
        _review(yday, "c", "메뉴 칸 없는 옛 리뷰", "돈가스", hour=13),
        _review(two, "d", "그제 돈가스", "돈가스", "images/two-donkatsu.jpg", menu=OLD_MENU),
    ], ensure_ascii=False), encoding="utf-8")
    body = app.app.test_client().get(f"/?day={yday.isoformat()}").get_data(as_text=True)
    tray = _tray(body)
    for dish in ("카레라이스", "맑은국", "돈가스", "단무지", "깍두기"):
        assert dish in tray
    assert "현미밥" not in tray  # 그날 가장 최근 메뉴(옛 리뷰는 건너뛴다)
    assert "알레르기 1.5.6" in tray and "리뷰 <strong>3</strong>" in tray
    assert "images/yday-donkatsu.jpg" in tray and "images/two-donkatsu.jpg" not in tray


def test_past_day_without_menu_record(monkeypatch, tmp_path):
    app = _load(monkeypatch, tmp_path)
    yday = app.today_kst() - timedelta(days=1)
    c = app.app.test_client()
    body = c.get(f"/?day={yday.isoformat()}").get_data(as_text=True)
    assert "이날 메뉴 기록이 없습니다" in body and "지난 메뉴는 보관하지 않습니다" not in body
    (tmp_path / "entries.json").write_text(json.dumps([_review(yday, "a", "옛 판 리뷰", "돈가스")], ensure_ascii=False),
                                         encoding="utf-8")
    body = c.get(f"/?day={yday.isoformat()}").get_data(as_text=True)
    assert "이날 메뉴 기록이 없습니다" in body and "옛 판 리뷰" in body


@mock_aws
def test_today_card_photo_keeps_latest_photo_regardless_of_day(monkeypatch, tmp_path):
    """오늘 식판 칸 사진은 날짜와 상관없이 그 메뉴의 가장 최근 사진(시연 서버가 자정에 비지 않게)."""
    _bucket("notice-test", MENU)
    app = _load(monkeypatch, tmp_path, NOTICE_BUCKET="notice-test", IMAGE_BUCKET="img-test")
    monkeypatch.setattr(app, "image_url", lambda k: f"https://img.example/{k}" if k else "")
    yday = app.today_kst() - timedelta(days=1)
    (tmp_path / "entries.json").write_text(json.dumps([
        _review(yday, "a", "어제 닭갈비", "닭갈비", "images/yday-dakgalbi.jpg", menu=MENU)], ensure_ascii=False), encoding="utf-8")
    assert "images/yday-dakgalbi.jpg" in _tray(app.app.test_client().get("/").get_data(as_text=True))


# --- 저장소 셋, 옛 판 서버와 같은 저장소 ---

def test_file_store_shared_with_old_code(monkeypatch, tmp_path):
    old = _old_storage(tmp_path).FileStore(tmp_path / "entries.json")
    old.add({"name": "옛판", "msg": "옛 판 서버가 쓴 리뷰", "image_key": "", "host": "ip-old", "dish": "돈가스"})
    saved = json.loads((tmp_path / "entries.json").read_text(encoding="utf-8"))
    saved[0]["ts"] -= 60  # 같은 초에 쓰면 앞뒤가 정해지지 않아서 1분 앞으로
    (tmp_path / "entries.json").write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
    app = _load(monkeypatch, tmp_path)
    monkeypatch.setattr(app, "read_notice_status", lambda: ("ok", MENU))
    app.app.test_client().post("/entries", data={"name": "새판", "msg": "새 판 서버가 쓴 리뷰"})
    assert [r["msg"] for r in app.store.list()] == ["새 판 서버가 쓴 리뷰", "옛 판 서버가 쓴 리뷰"]
    assert [r["msg"] for r in old.list()] == ["새 판 서버가 쓴 리뷰", "옛 판 서버가 쓴 리뷰"]  # 옛 판도 그대로 읽는다
    old.add({"name": "옛판2", "msg": "옛 판이 나중에 쓴 리뷰", "image_key": "", "host": "", "dish": ""})
    kept = {r["msg"]: r for r in app.store.list()}
    assert kept["새 판 서버가 쓴 리뷰"]["menu"] == MENU  # 옛 판이 파일을 다시 써도 새 판의 menu 는 남는다


def _ddb_table():
    import boto3

    boto3.client("dynamodb", region_name="ap-northeast-2").create_table(
        TableName="guestbook", KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}], BillingMode="PAY_PER_REQUEST")
    return boto3.resource("dynamodb", region_name="ap-northeast-2").Table("guestbook")


@mock_aws
def test_dynamodb_menu_inside_review_shared_with_old_code(monkeypatch, tmp_path):
    table = _ddb_table()
    _bucket("notice-test", MENU)
    monkeypatch.setenv("AWS_DEFAULT_REGION", "ap-northeast-2")
    monkeypatch.setenv("DYNAMODB_TABLE", "guestbook")
    app = _load(monkeypatch, tmp_path, STORAGE="dynamodb", DYNAMODB_TABLE="guestbook", NOTICE_BUCKET="notice-test")
    ops = []
    app.store.table.meta.client.meta.events.register("before-call.dynamodb.*", lambda model, **k: ops.append(model.name))
    c = app.app.test_client()
    c.post("/entries", data={"name": "새판", "msg": "새 판 리뷰", "dish": "닭갈비"})
    c.get("/")
    items = table.scan()["Items"]
    assert len(items) == 1 and items[0]["menu"] == MENU  # 메뉴 항목을 따로 만들지 않는다
    assert set(ops) <= {"Scan", "PutItem"}, ops  # 런북 정책(Scan, PutItem)만
    old = _old_storage(tmp_path).DynamoStore()
    old.add({"name": "옛판", "msg": "옛 판 리뷰", "image_key": "", "host": "", "dish": ""})
    assert sorted(r["msg"] for r in old.list()) == ["새 판 리뷰", "옛 판 리뷰"]
    assert sorted(r["msg"] for r in app.store.list()) == ["새 판 리뷰", "옛 판 리뷰"]


@mock_aws
def test_mysql_menu_column_on_old_table_shared_with_old_code(monkeypatch, mysql_port, tmp_path):
    import boto3
    import pymysql

    with pymysql.connect(host="127.0.0.1", port=mysql_port, user="root", password="pw", database="guestbook") as conn:
        with conn.cursor() as cur:  # 방명록 때 만든 표(host, dish, menu 없음)
            cur.execute("CREATE TABLE entries (id VARCHAR(36) PRIMARY KEY, ts BIGINT, name VARCHAR(30),"
                        " msg VARCHAR(300), image_key VARCHAR(200))")
        conn.commit()
    ssm = boto3.client("ssm", region_name="ap-northeast-2")
    ssm.put_parameter(Name="/guestbook/db/host", Type="String", Value="127.0.0.1")
    ssm.put_parameter(Name="/guestbook/db/password", Type="SecureString", Value="pw")
    for k, v in {"DB_USER": "root", "DB_PORT": str(mysql_port), "AWS_DEFAULT_REGION": "ap-northeast-2",
                 "AWS_ACCESS_KEY_ID": "testing", "AWS_SECRET_ACCESS_KEY": "testing"}.items():
        monkeypatch.setenv(k, v)
    old = _old_storage(tmp_path).MySQLStore()  # 옛 판이 host, dish 칸을 더한다
    _bucket("notice-test", MENU)
    app = _load(monkeypatch, tmp_path, STORAGE="mysql", DB_USER="root", DB_PORT=str(mysql_port), NOTICE_BUCKET="notice-test")
    app.app.test_client().post("/entries", data={"name": "새판", "msg": "새 판 리뷰", "dish": "닭갈비"})
    old.add({"name": "옛판", "msg": "옛 판 리뷰", "image_key": "", "host": "", "dish": ""})
    new_items = {r["msg"]: r for r in app.store.list()}
    assert new_items["새 판 리뷰"]["menu"] == MENU and new_items["옛 판 리뷰"]["menu"] == ""
    assert sorted(r["msg"] for r in old.list()) == ["새 판 리뷰", "옛 판 리뷰"]
    _load(monkeypatch, tmp_path, STORAGE="mysql", DB_USER="root", DB_PORT=str(mysql_port))  # 두 번 켜도 된다


# --- 설정 견본, 5MB, notice.txt, 문구, 판 ---

def test_hello_api_url_is_last_line_of_config_example():
    """13단원은 「설정 파일 맨 아래 HELLO_API_URL=」을 고친다."""
    lines = [l for l in (ROOT / "config.env.example").read_text(encoding="utf-8").splitlines() if l.strip()]
    assert lines[-1] == "HELLO_API_URL="


def test_photo_over_5mb_shows_korean_message(monkeypatch, tmp_path):
    app = _load(monkeypatch, tmp_path, IMAGE_BUCKET="img-test")
    c = app.app.test_client()
    big = io.BytesIO(b"0" * (5 * 1024 * 1024 + 10))
    r = c.post("/entries", data={"name": "a", "msg": "큰 사진", "image": (big, "big.jpg")}, content_type="multipart/form-data")
    assert r.status_code == 302 and "error=toolarge" in r.headers["Location"]
    assert "사진이 5MB 를 넘습니다" in c.get("/?error=toolarge").get_data(as_text=True)
    js = (ROOT / "static" / "app" / "app.js").read_text(encoding="utf-8")
    assert "5 * 1024 * 1024" in js and "5MB" in js  # 올리기 전에 브라우저에서 먼저 막는다


@mock_aws
def test_notice_with_bom_is_read_as_menu(monkeypatch, tmp_path):
    """메모장 등이 붙이는 BOM 이 첫 줄(밥)을 망가뜨리지 않는다."""
    _bucket("notice-test", raw="\ufeff".encode("utf-8") + MENU.encode())
    app = _load(monkeypatch, tmp_path, NOTICE_BUCKET="notice-test")
    tray = _tray(app.app.test_client().get("/").get_data(as_text=True))
    assert "현미밥" in tray and "밥 칸" not in tray


@mock_aws
def test_plain_notice_hides_comment_lines(monkeypatch, tmp_path):
    _bucket("notice-test", "# 메모: 오늘은 메뉴 없음\n공지: 내일은 특식입니다.")
    app = _load(monkeypatch, tmp_path, NOTICE_BUCKET="notice-test")
    body = app.app.test_client().get("/").get_data(as_text=True)
    assert "공지: 내일은 특식입니다." in body and "메모: 오늘은 메뉴 없음" not in body


@mock_aws
def test_wording_and_version(monkeypatch, tmp_path):
    app = _load(monkeypatch, tmp_path, NOTICE_BUCKET="no-such-bucket")
    c = app.app.test_client()
    body = c.get("/").get_data(as_text=True)
    assert "(오늘 메뉴를 읽지 못했습니다: NoSuchBucket)" in body and "공지를 읽지 못했습니다" not in body
    assert c.get("/health").get_json()["notice"] == "error"
    assert app.APP_VERSION == "2.1.0" and "v2.1.0" in body
    yday = app.today_kst() - timedelta(days=1)
    assert "그날 쓴 리뷰가 없습니다" in c.get(f"/?day={yday.isoformat()}").get_data(as_text=True)


def test_mysql_added_column_race_is_ignored(monkeypatch, tmp_path):
    """서버 두 대가 함께 켜져 둘 다 칸이 없다고 보고 ALTER 하면 늦은 쪽은 1060(이미 있는 칸)을 받는다. 그래도 켜진다."""
    import pymysql

    app = _load(monkeypatch, tmp_path)
    storage = sys.modules["storage"]

    class Cur:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def execute(self, sql, *a):
            if sql.startswith("ALTER TABLE"):
                raise pymysql.err.OperationalError(1060, "Duplicate column name 'menu'")

        def fetchall(self):
            return [{"Field": f} for f in ("id", "ts", "name", "msg", "image_key")]

    class Conn:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def cursor(self):
            return Cur()

        def commit(self):
            pass

    monkeypatch.setattr(storage, "_ssm_param", lambda *a, **k: "x")
    monkeypatch.setattr(pymysql, "connect", lambda **k: Conn())
    storage.MySQLStore()  # 예외 없이 켜진다
