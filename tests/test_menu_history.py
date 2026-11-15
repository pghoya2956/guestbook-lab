"""지난 날 메뉴: 오늘 notice.txt 메뉴를 리뷰와 같은 저장소에 남기고, 지난 날 화면은 그 기록으로 식판을 그린다."""
import importlib
import io
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from moto import mock_aws

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

KST = timezone(timedelta(hours=9))
MENU = "밥|현미밥|\n국|소고기미역국|5.6.16\n반찬|닭갈비|5.6.13.15\n반찬|콩나물무침|5.6\n반찬|배추김치|9.13\n후식|귤|\n열량|812\n"
OLD_MENU = "밥|카레라이스|5.6\n국|맑은국|\n반찬|돈가스|1.5.6\n반찬|단무지|\n반찬|깍두기|9.13\n"


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


def _bucket(name, body=None):
    import boto3

    s3 = boto3.client("s3", region_name="ap-northeast-2")
    s3.create_bucket(Bucket=name, CreateBucketConfiguration={"LocationConstraint": "ap-northeast-2"})
    if body is not None:
        s3.put_object(Bucket=name, Key="notice.txt", Body=body.encode())
    return s3


def _days(app):
    today = app.today_kst()
    return today, today - timedelta(days=1)


def _ts(d, hour=12):
    return int(datetime(d.year, d.month, d.day, hour, tzinfo=KST).timestamp())


def _review(d, name, msg, dish="", image_key="", host="ip-10-0-1-24"):
    return {"id": f"{name}-{d}", "ts": _ts(d), "name": name, "msg": msg, "image_key": image_key, "host": host, "dish": dish}


# --- 오늘 메뉴를 저장소에 남긴다 ---

@mock_aws
def test_file_store_saves_todays_menu_only_when_changed(monkeypatch, tmp_path):
    s3 = _bucket("notice-test", MENU)
    app = _load(monkeypatch, tmp_path, NOTICE_BUCKET="notice-test")
    today, _ = _days(app)
    calls = []
    real = app.store.save_menu
    monkeypatch.setattr(app.store, "save_menu", lambda d, t: (calls.append(d), real(d, t)))
    c = app.app.test_client()
    for _ in range(3):
        c.get("/")
    saved = json.loads((tmp_path / "menus.json").read_text(encoding="utf-8"))
    assert saved[today.isoformat()]["notice"] == MENU.strip() and calls == [today.isoformat()]
    s3.put_object(Bucket="notice-test", Key="notice.txt", Body=OLD_MENU.encode())  # 같은 날 메뉴가 바뀌면 덮는다
    body = c.get("/").get_data(as_text=True)
    c.get("/")
    assert app.store.get_menu(today.isoformat()) == OLD_MENU.strip() and len(calls) == 2
    # 9단원 도전: notice.txt 를 바꾸면 재시작 없이 바로 바뀐다. 오늘 식판은 저장소가 아니라 S3 에서 읽는다
    assert "돈가스" in body and "닭갈비" not in body.split('id="menu"')[1].split("</section>")[0]


@mock_aws
def test_plain_notice_or_errors_are_not_saved_as_menu(monkeypatch, tmp_path):
    _bucket("notice-test", "공지: 오늘은 특식입니다.")
    app = _load(monkeypatch, tmp_path, NOTICE_BUCKET="notice-test")
    app.app.test_client().get("/")
    assert app.store.get_menu(app.today_kst().isoformat()) is None
    app = _load(monkeypatch, tmp_path, NOTICE_BUCKET="no-such-bucket")
    app.app.test_client().get("/")
    assert app.store.get_menu(app.today_kst().isoformat()) is None


def test_menu_save_failure_keeps_page_up(monkeypatch, tmp_path):
    app = _load(monkeypatch, tmp_path)
    monkeypatch.setattr(app, "read_notice_status", lambda: ("ok", MENU))

    def boom(*a):
        raise PermissionError("AccessDeniedException")

    monkeypatch.setattr(app.store, "save_menu", boom)
    r = app.app.test_client().get("/")
    assert r.status_code == 200 and "닭갈비" in r.get_data(as_text=True)


# --- 지난 날 식판 ---

def test_past_day_tray_from_saved_menu_with_that_days_photos_and_counts(monkeypatch, tmp_path):
    app = _load(monkeypatch, tmp_path, IMAGE_BUCKET="img-test")
    monkeypatch.setattr(app, "image_url", lambda k: f"https://img.example/{k}" if k else "")
    today, yday = _days(app)
    two = yday - timedelta(days=1)
    (tmp_path / "entries.json").write_text(json.dumps([
        _review(yday, "a", "돈가스 바삭", "돈가스", "images/yday-donkatsu.jpg"),
        _review(yday, "b", "돈가스 최고", "돈가스"),
        _review(two, "c", "그제 돈가스", "돈가스", "images/two-donkatsu.jpg"),
        _review(today, "d", "오늘 리뷰"),
    ], ensure_ascii=False), encoding="utf-8")
    app.store.save_menu(yday.isoformat(), OLD_MENU)
    body = app.app.test_client().get(f"/?day={yday.isoformat()}").get_data(as_text=True)
    for dish in ("카레라이스", "맑은국", "돈가스", "단무지", "깍두기"):
        assert dish in body
    assert "알레르기 1.5.6" in body and "리뷰 <strong>2</strong>" in body
    assert "images/yday-donkatsu.jpg" in body and "images/two-donkatsu.jpg" not in body  # 그날 사진만
    assert "리뷰 가장 많음" in body
    assert "오늘 리뷰" not in body and "지난 메뉴는 보관하지 않습니다" not in body


def test_past_day_without_record_uses_review_dish_names(monkeypatch, tmp_path):
    app = _load(monkeypatch, tmp_path)
    _, yday = _days(app)
    (tmp_path / "entries.json").write_text(json.dumps([
        _review(yday, "a", "a", "짜장면"), _review(yday, "b", "b", "탕수육"), _review(yday, "c", "c", "짜장면"),
    ], ensure_ascii=False), encoding="utf-8")
    body = app.app.test_client().get(f"/?day={yday.isoformat()}").get_data(as_text=True)
    assert "짜장면" in body and "탕수육" in body and "리뷰에 적힌 메뉴로" in body
    assert "알레르기 없음" not in body  # 알레르기는 모르니 적지 않는다


def test_past_day_without_anything(monkeypatch, tmp_path):
    app = _load(monkeypatch, tmp_path)
    _, yday = _days(app)
    body = app.app.test_client().get(f"/?day={yday.isoformat()}").get_data(as_text=True)
    assert "이날 메뉴 기록이 없습니다" in body and "지난 메뉴는 보관하지 않습니다" not in body


@mock_aws
def test_today_card_photo_uses_only_todays_photo_reviews(monkeypatch, tmp_path):
    """오늘 식판도 지난 날 화면처럼 그날 올라온 사진만 칸에 쓴다(리뷰 수를 오늘만 세는 것과 같다)."""
    _bucket("notice-test", MENU)
    app = _load(monkeypatch, tmp_path, NOTICE_BUCKET="notice-test", IMAGE_BUCKET="img-test")
    monkeypatch.setattr(app, "image_url", lambda k: f"https://img.example/{k}" if k else "")
    today, yday = _days(app)
    (tmp_path / "entries.json").write_text(json.dumps([
        _review(yday, "a", "어제 닭갈비", "닭갈비", "images/yday-dakgalbi.jpg"),
    ], ensure_ascii=False), encoding="utf-8")
    c = app.app.test_client()
    assert "slot-img" not in c.get("/").get_data(as_text=True)
    (tmp_path / "entries.json").write_text(json.dumps([
        _review(yday, "a", "어제 닭갈비", "닭갈비", "images/yday-dakgalbi.jpg"),
        _review(today, "b", "오늘 닭갈비", "닭갈비", "images/today-dakgalbi.jpg"),
    ], ensure_ascii=False), encoding="utf-8")
    body = c.get("/").get_data(as_text=True)
    assert "images/today-dakgalbi.jpg" in body.split('class="slot-img"')[1][:200]


# --- DynamoDB: 같은 테이블, 리뷰와 섞이지 않게, Scan 과 PutItem 만 ---

def _ddb_table():
    import boto3

    boto3.client("dynamodb", region_name="ap-northeast-2").create_table(
        TableName="guestbook", KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}], BillingMode="PAY_PER_REQUEST")
    return boto3.resource("dynamodb", region_name="ap-northeast-2").Table("guestbook")


@mock_aws
def test_dynamodb_menu_in_same_table_kept_out_of_reviews(monkeypatch, tmp_path):
    _bucket("notice-test", MENU)
    table = _ddb_table()
    app = _load(monkeypatch, tmp_path, STORAGE="dynamodb", DYNAMODB_TABLE="guestbook", NOTICE_BUCKET="notice-test")
    # 런북 메뉴 2 정책은 Scan 과 PutItem 만 준다. 다른 작업(GetItem, Query 등)을 부르면 실제 계정에서 AccessDenied 다
    ops = []
    app.store.table.meta.client.meta.events.register("before-call.dynamodb.*", lambda model, **k: ops.append(model.name))
    today, yday = _days(app)
    c = app.app.test_client()
    c.post("/entries", data={"name": "a", "msg": "리뷰 하나", "dish": "닭갈비"})
    body = c.get("/").get_data(as_text=True)
    assert "리뷰 <strong>1</strong>" in body and ">리뷰 1<" in body.replace("</h2>", "<")
    assert app.store.get_menu(today.isoformat()) == MENU.strip()
    assert [i["msg"] for i in app.store.list()] == ["리뷰 하나"]
    assert len(table.scan()["Items"]) == 2  # 리뷰 하나와 메뉴 하나
    app.store.save_menu(yday.isoformat(), OLD_MENU)
    body = c.get(f"/?day={yday.isoformat()}").get_data(as_text=True)
    assert "돈가스" in body and "카레라이스" in body
    assert ops and set(ops) <= {"Scan", "PutItem"}, ops


# --- MySQL: 예전 테이블에서 켜지고 menus 표를 만든다 ---

@mock_aws
def test_mysql_menu_history_on_old_database(monkeypatch, mysql_port, tmp_path):
    import boto3
    import pymysql

    with pymysql.connect(host="127.0.0.1", port=mysql_port, user="root", password="pw", database="guestbook") as c:
        with c.cursor() as cur:
            cur.execute("CREATE TABLE entries (id VARCHAR(36) PRIMARY KEY, ts BIGINT, name VARCHAR(30),"
                        " msg VARCHAR(300), image_key VARCHAR(200))")
        c.commit()
    ssm = boto3.client("ssm", region_name="ap-northeast-2")
    ssm.put_parameter(Name="/guestbook/db/host", Type="String", Value="127.0.0.1")
    ssm.put_parameter(Name="/guestbook/db/password", Type="SecureString", Value="pw")
    _bucket("notice-test", MENU)
    app = _load(monkeypatch, tmp_path, STORAGE="mysql", DB_USER="root", DB_PORT=str(mysql_port), NOTICE_BUCKET="notice-test")
    today, yday = _days(app)
    c = app.app.test_client()
    c.get("/")
    assert app.store.get_menu(today.isoformat()) == MENU.strip()
    app.store.save_menu(today.isoformat(), OLD_MENU)  # 같은 날은 덮는다
    assert app.store.get_menu(today.isoformat()) == OLD_MENU
    app.store.save_menu(yday.isoformat(), OLD_MENU)
    assert "돈가스" in c.get(f"/?day={yday.isoformat()}").get_data(as_text=True)
    assert app.store.get_menu("2000-01-01") is None
    _load(monkeypatch, tmp_path, STORAGE="mysql", DB_USER="root", DB_PORT=str(mysql_port))  # 두 번 켜도 된다


# --- 검토에서 나온 것 ---

def test_menu_is_rechecked_after_a_minute_across_servers(monkeypatch, tmp_path):
    """서버 A 가 기억한 메뉴와 저장소가 어긋나면(다른 서버가 잠깐 잘못 올라온 메뉴를 씀) 1분 안에 바로잡는다.
    실패해도 1분에 한 번만 다시 해 본다."""
    app = _load(monkeypatch, tmp_path)
    today = app.today_kst().isoformat()
    clock = [1000.0]
    monkeypatch.setattr(app.time, "time", lambda: clock[0])
    app.remember_menu(today, MENU)
    app.store.save_menu(today, "밥|오타밥|")  # 다른 서버가 쓴 값
    app.remember_menu(today, MENU)
    assert app.store.get_menu(today) == "밥|오타밥|"  # 1분 안에는 저장소를 다시 보지 않는다
    clock[0] += 61
    app.remember_menu(today, MENU)
    assert app.store.get_menu(today) == MENU
    calls = []

    def boom(*a):
        calls.append(a)
        raise PermissionError("AccessDeniedException")

    monkeypatch.setattr(app.store, "save_menu", boom)
    for _ in range(5):
        app.remember_menu(today, OLD_MENU)
    assert len(calls) == 1
    clock[0] += 61
    app.remember_menu(today, OLD_MENU)
    assert len(calls) == 2


def test_kst_midnight_review_belongs_to_kst_day(monkeypatch, tmp_path):
    """KST 0시 30분(UTC 로는 전날 15시 30분)에 쓴 리뷰는 KST 날짜의 식판에 든다."""
    app = _load(monkeypatch, tmp_path)
    _, yday = _days(app)
    early = int(datetime(yday.year, yday.month, yday.day, 0, 30, tzinfo=KST).timestamp())
    late = int(datetime(yday.year, yday.month, yday.day, 23, 50, tzinfo=KST).timestamp())
    (tmp_path / "entries.json").write_text(json.dumps([
        {"id": "e", "ts": early, "name": "a", "msg": "새벽 리뷰", "image_key": "", "host": "", "dish": "돈가스"},
        {"id": "l", "ts": late, "name": "b", "msg": "밤 리뷰", "image_key": "", "host": "", "dish": "돈가스"},
        {"id": "p", "ts": early - 3600, "name": "c", "msg": "하루 앞선 글", "image_key": "", "host": "", "dish": "돈가스"},
    ], ensure_ascii=False), encoding="utf-8")
    app.store.save_menu(yday.isoformat(), OLD_MENU)
    body = app.app.test_client().get(f"/?day={yday.isoformat()}").get_data(as_text=True)
    assert "새벽 리뷰" in body and "밤 리뷰" in body and "하루 앞선 글" not in body
    assert "리뷰 <strong>2</strong>" in body


@mock_aws
def test_lambda_api_list_skips_menu_items(monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "ap-northeast-2")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    table = _ddb_table()
    table.put_item(Item={"id": "r1", "ts": 1, "name": "a", "msg": "리뷰"})
    table.put_item(Item={"id": "menu#2026-11-15", "kind": "menu", "notice": MENU})
    sys.path.insert(0, str(ROOT / "lambda" / "api"))
    sys.modules.pop("lambda_function", None)
    mod = importlib.import_module("lambda_function")
    sys.modules.pop("lambda_function", None)
    out = mod.lambda_handler({"requestContext": {"http": {"method": "GET"}}}, None)
    assert [i["msg"] for i in json.loads(out["body"])] == ["리뷰"]


def test_broken_menus_file_recovers_on_next_save(monkeypatch, tmp_path):
    """menus.json 이 깨져 있어도(쓰다 끊김 등) 화면은 뜨고 오늘 메뉴를 다시 남긴다."""
    app = _load(monkeypatch, tmp_path)
    today = app.today_kst().isoformat()
    (tmp_path / "menus.json").write_text('{"2026-11-1', encoding="utf-8")
    assert app.store.get_menu(today) is None
    app.store.save_menu(today, MENU)
    assert app.store.get_menu(today) == MENU
    assert not list(tmp_path.glob("*.tmp"))  # 임시 파일을 남기지 않는다


@mock_aws
def test_dynamodb_menu_lookup_follows_scan_pages(monkeypatch, tmp_path):
    """테이블이 커서 Scan 이 여러 쪽으로 나뉘어도 메뉴를 찾는다."""
    _ddb_table()
    app = _load(monkeypatch, tmp_path, STORAGE="dynamodb", DYNAMODB_TABLE="guestbook")
    pages = [{"Items": [], "LastEvaluatedKey": {"id": "x"}}, {"Items": [{"id": "menu#2026-11-14", "notice": OLD_MENU}]}]
    seen = []
    monkeypatch.setattr(app.store.table, "scan", lambda **k: (seen.append(k.get("ExclusiveStartKey")), pages[len(seen) - 1])[1])
    assert app.store.get_menu("2026-11-14") == OLD_MENU and seen == [None, {"id": "x"}]
