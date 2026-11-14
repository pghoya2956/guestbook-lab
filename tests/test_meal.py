"""급식 리뷰 앱에서 더한 것: 메뉴 형식, 새 필드(host, dish), 강사 판정이 기대는 화면 줄, 오류 상태."""
import html
import importlib
import json
import re
import sys
import time
from pathlib import Path

import pytest
from moto import mock_aws

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# 강사 진척 판정(aws-lab observe/checks.py)과 같은 규칙. 본문 앞 8192 바이트만 읽는다
HTTP_BYTES = 8192
HELLO_LINE = re.compile(r'<p class="hello">오늘의 한마디:\s*(.*?)\s*</p>', re.S)
HOST_LINE = re.compile(r"서버: <b>(.*?)</b>")

MENU = """# 주석은 화면에 안 나온다
밥|현미밥|
국|소고기미역국|5.6.16
반찬|닭갈비|5.6.13.15
반찬|콩나물무침|5.6
반찬|배추김치|9.13
후식|귤|
열량|812
공지: 내일은 특식입니다.
"""


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


def _notice_bucket(body):
    import boto3

    s3 = boto3.client("s3", region_name="ap-northeast-2")
    s3.create_bucket(Bucket="notice-test", CreateBucketConfiguration={"LocationConstraint": "ap-northeast-2"})
    s3.put_object(Bucket="notice-test", Key="notice.txt", Body=body.encode())


# --- 메뉴 형식 ---

def test_parse_menu_reads_slots(monkeypatch, tmp_path):
    app = _load(monkeypatch, tmp_path)
    m = app.parse_menu(MENU)
    assert m["rice"] == {"name": "현미밥", "allergy": ""}
    assert m["soup"] == {"name": "소고기미역국", "allergy": "5.6.16"}
    assert [d["name"] for d in m["sides"]] == ["닭갈비", "콩나물무침", "배추김치"]
    assert m["dessert"]["name"] == "귤" and m["kcal"] == "812"
    assert m["notes"] == ["공지: 내일은 특식입니다."]


def test_parse_menu_falls_back_to_notice(monkeypatch, tmp_path):
    """메뉴 줄이 하나도 없으면 None 이고, 화면은 예전처럼 글 전체를 공지로 보인다."""
    app = _load(monkeypatch, tmp_path)
    assert app.parse_menu("공지: 이 문장은 S3 버킷의 notice.txt 에서 읽어 왔습니다.") is None
    assert app.parse_menu("") is None
    assert app.parse_menu("밥|\n국") is None  # 음식 이름이 빈 줄은 메뉴가 아니다


def test_parse_menu_extra_rows_and_numbered_sides(monkeypatch, tmp_path):
    app = _load(monkeypatch, tmp_path)
    m = app.parse_menu("반찬1|김|\n반찬 2|계란말이|1\n밥|흰밥|\n밥|볶음밥|5\n|빈칸|")
    assert [d["name"] for d in m["sides"]] == ["김", "계란말이", "볶음밥"]  # 두 번째 밥은 반찬 칸으로
    assert m["rice"]["name"] == "흰밥" and m["soup"] is None
    assert m["notes"] == ["|빈칸|"]


@mock_aws
def test_index_shows_menu_tray_with_counts(monkeypatch, tmp_path):
    _notice_bucket(MENU)
    app = _load(monkeypatch, tmp_path, NOTICE_BUCKET="notice-test")
    c = app.app.test_client()
    for dish in ("닭갈비", "닭갈비", "소고기미역국", ""):
        c.post("/entries", data={"name": "새벽코딩", "msg": "맛있어요", "dish": dish})
    body = c.get("/").get_data(as_text=True)
    assert "닭갈비" in body and "알레르기 5.6.13.15" in body and "알레르기 없음" in body
    assert "812" in body and "내일은 특식입니다" in body
    assert body.count("리뷰 가장 많음") == 1
    top = body.index("리뷰 가장 많음")
    assert body.index("닭갈비", top) < body.index("콩나물무침")  # 강조는 닭갈비 칸
    assert '<option>소고기미역국</option>' in body  # 리뷰 쓰기에서 메뉴를 고를 수 있다
    assert c.get("/health").get_json()["notice"] == "ok"


@mock_aws
def test_index_shows_plain_notice_and_errors(monkeypatch, tmp_path):
    _notice_bucket("공지: 이 문장은 S3 버킷의 notice.txt 에서 읽어 왔습니다.")
    app = _load(monkeypatch, tmp_path, NOTICE_BUCKET="notice-test")
    body = app.app.test_client().get("/").get_data(as_text=True)
    assert "공지: 이 문장은 S3 버킷의 notice.txt 에서 읽어 왔습니다." in body
    assert "리뷰 가장 많음" not in body
    app = _load(monkeypatch, tmp_path, NOTICE_BUCKET="no-such-bucket")
    body = app.app.test_client().get("/").get_data(as_text=True)
    assert "(공지를 읽지 못했습니다: NoSuchBucket)" in body
    app = _load(monkeypatch, tmp_path)
    assert "아직 오늘 메뉴가 없습니다" in app.app.test_client().get("/").get_data(as_text=True)


# --- 새 필드 host, dish ---

def test_review_keeps_receiving_host_and_dish(monkeypatch, tmp_path):
    app = _load(monkeypatch, tmp_path)
    monkeypatch.setattr(app.socket, "gethostname", lambda: "ip-10-0-2-81")
    c = app.app.test_client()
    c.post("/entries", data={"name": "바다거북", "msg": "미역국 진했어요", "dish": "소고기미역국"})
    saved = json.loads((tmp_path / "entries.json").read_text(encoding="utf-8"))[0]
    assert saved["host"] == "ip-10-0-2-81" and saved["dish"] == "소고기미역국" and saved["image_key"] == ""
    body = c.get("/").get_data(as_text=True)
    assert "받은 서버 <span class=\"mono\">ip-10-0-2-81</span>" in body


def test_old_entries_without_new_fields_are_listed(monkeypatch, tmp_path):
    """방명록 때 쓴 글(host, dish 없음)과 서버리스 API 가 쓴 글(image_key 도 없음)이 그대로 읽힌다."""
    old = [
        {"id": "a", "ts": int(time.time()) - 60, "name": "민수", "msg": "방명록 때 글", "image_key": ""},
        {"id": "b", "ts": int(time.time()) - 30, "name": "", "msg": "API 로 쓴 글"},
    ]
    (tmp_path / "entries.json").write_text(json.dumps(old, ensure_ascii=False), encoding="utf-8")
    app = _load(monkeypatch, tmp_path)
    items = app.store.list()
    assert [i["msg"] for i in items] == ["API 로 쓴 글", "방명록 때 글"]
    assert all(i["host"] == "" and i["dish"] == "" and i["image_key"] == "" for i in items)
    assert items[0]["name"] == "익명"
    body = app.app.test_client().get("/").get_data(as_text=True)
    assert "방명록 때 글" in body and "API 로 쓴 글" in body and "받은 서버" not in body


@mock_aws
def test_dynamodb_old_items_and_new_fields(monkeypatch, tmp_path):
    import boto3

    boto3.client("dynamodb", region_name="ap-northeast-2").create_table(
        TableName="guestbook",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    table = boto3.resource("dynamodb", region_name="ap-northeast-2").Table("guestbook")
    table.put_item(Item={"id": "old", "ts": int(time.time()) - 60, "name": "민수", "msg": "API 로 쓴 글"})
    app = _load(monkeypatch, tmp_path, STORAGE="dynamodb", DYNAMODB_TABLE="guestbook")
    c = app.app.test_client()
    c.post("/entries", data={"name": "귤", "msg": "새 글", "dish": "귤"})
    items = app.store.list()
    assert [i["msg"] for i in items] == ["새 글", "API 로 쓴 글"]
    assert items[0]["host"] and items[0]["dish"] == "귤" and items[1]["host"] == ""
    assert isinstance(items[1]["ts"], int)


# --- 강사 판정이 기대는 화면 줄 ---

def test_hello_and_host_lines_match_instructor_checks(monkeypatch, tmp_path):
    """13단원 판정: 본문 앞 8KB 안에 「오늘의 한마디:」 줄과 「서버: <b>호스트</b>」가 있다. 앱 안 목록이면 local 로 읽힌다."""
    app = _load(monkeypatch, tmp_path)
    c = app.app.test_client()
    for i in range(30):
        c.post("/entries", data={"name": "긴별명" * 10, "msg": "가" * 300})
    head = c.get("/").get_data()[:HTTP_BYTES].decode("utf-8", "replace")
    m = HELLO_LINE.search(head)
    assert m and html.unescape(m[1]).strip() in app.LOCAL_HELLO
    h = HOST_LINE.search(head)
    assert h and h[1] == app.socket.gethostname()
    tpl = (ROOT / "templates" / "index.html").read_text(encoding="utf-8")
    assert '서버: <b>{{ host }}</b>' in tpl
    assert HELLO_LINE.search(tpl.replace("{{ hello }}", "내 문장"))[1] == "내 문장"


def test_lambda_hello_is_shown_with_source(monkeypatch, tmp_path):
    app = _load(monkeypatch, tmp_path, HELLO_API_URL="http://example.invalid/hello")

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps({"message": "미역국이 진해요. 국부터 드세요."}).encode()

    monkeypatch.setattr(app.urllib.request, "urlopen", lambda *a, **k: Resp())
    body = app.app.test_client().get("/").get_data(as_text=True)
    assert HELLO_LINE.search(body)[1] == "미역국이 진해요. 국부터 드세요."
    assert re.search(r"Lambda <span class=\"wide-only\">가 </span>\d+ms", body)

    def boom(*a, **k):
        raise TimeoutError()

    monkeypatch.setattr(app.urllib.request, "urlopen", boom)
    body = app.app.test_client().get("/").get_data(as_text=True)
    assert HELLO_LINE.search(body)[1] == "(한마디 API 오류: TimeoutError)"  # 판정이 error 로 읽는 머리말


# --- 오류 상태 ---

def test_storage_error_is_shown_not_500(monkeypatch, tmp_path):
    app = _load(monkeypatch, tmp_path)

    class Broken:
        name = "dynamodb"

        def list(self, limit=50):
            raise PermissionError("AccessDeniedException")

        def add(self, entry):
            raise PermissionError("AccessDeniedException")

    monkeypatch.setattr(app, "store", Broken())
    c = app.app.test_client()
    r = c.get("/")
    body = r.get_data(as_text=True)
    assert r.status_code == 200 and "리뷰 저장소" in body and "PermissionError" in body
    assert "저장소: <b>dynamodb</b> 오류" in body
    r = c.post("/entries", data={"name": "a", "msg": "b"})
    assert r.status_code == 302 and "error=save" in r.headers["Location"]
    assert "리뷰를 저장하지 못했습니다" in c.get("/?error=save").get_data(as_text=True)
    assert c.get("/health").get_json()["storage"] == "dynamodb"


def test_past_day_shows_only_that_days_reviews(monkeypatch, tmp_path):
    now = int(time.time())
    items = [
        {"id": "a", "ts": now - 86400, "name": "어제", "msg": "어제 리뷰", "image_key": "", "host": "", "dish": ""},
        {"id": "b", "ts": now, "name": "오늘", "msg": "오늘 리뷰", "image_key": "", "host": "", "dish": ""},
    ]
    (tmp_path / "entries.json").write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    app = _load(monkeypatch, tmp_path)
    c = app.app.test_client()
    yday = (app.today_kst() - app.timedelta(days=1)).isoformat()
    body = c.get(f"/?day={yday}").get_data(as_text=True)
    assert "어제 리뷰" in body and "오늘 리뷰" not in body and "지난 메뉴는 보관하지 않습니다" in body
    body = c.get("/").get_data(as_text=True)
    assert "어제 리뷰" in body and "오늘 리뷰" in body  # 오늘 보기는 최근 리뷰 전체
    assert "오늘 리뷰" in c.get("/?day=2999-01-01").get_data(as_text=True)  # 미래 날짜는 오늘 보기


def test_long_text_is_escaped(monkeypatch, tmp_path):
    app = _load(monkeypatch, tmp_path)
    c = app.app.test_client()
    c.post("/entries", data={"name": "<b>x</b>", "msg": "<script>alert(1)</script>" + "가" * 400})
    body = c.get("/").get_data(as_text=True)
    assert "<script>alert(1)</script>" not in body and "&lt;script&gt;" in body
    saved = json.loads((tmp_path / "entries.json").read_text(encoding="utf-8"))[0]
    assert len(saved["msg"]) == 300


# --- 검토에서 나온 것 ---

@mock_aws
def test_tray_counts_only_todays_reviews(monkeypatch, tmp_path):
    """매일 나오는 반찬(김치)이 지난 날 리뷰 때문에 「리뷰 가장 많음」이 되지 않는다."""
    _notice_bucket(MENU)
    now = int(time.time())
    old = [{"id": str(i), "ts": now - 86400 * 2, "name": "a", "msg": "김치", "image_key": "", "host": "", "dish": "배추김치"}
           for i in range(5)]
    (tmp_path / "entries.json").write_text(json.dumps(old, ensure_ascii=False), encoding="utf-8")
    app = _load(monkeypatch, tmp_path, NOTICE_BUCKET="notice-test")
    c = app.app.test_client()
    body = c.get("/").get_data(as_text=True)
    assert "리뷰 가장 많음" not in body
    c.post("/entries", data={"name": "b", "msg": "맛있다", "dish": "닭갈비"})
    body = c.get("/").get_data(as_text=True)
    assert body.count("리뷰 가장 많음") == 1 and body.index("닭갈비", body.index("리뷰 가장 많음")) < body.index("콩나물무침")


def test_fourth_side_dish_fills_the_tray_row(monkeypatch, tmp_path):
    app = _load(monkeypatch, tmp_path)
    for n, want in ((0, 3), (2, 1), (3, 0), (4, 2), (6, 0)):
        menu, _ = app._menu_view("ok", "\n".join(f"반찬|반찬{i}|" for i in range(n)) + "\n밥|밥|", [])
        assert menu["empty_sides"] == want, n


def test_lambda_null_message_is_empty(monkeypatch, tmp_path):
    """함수가 message 를 null 로 주면 「None」이 아니라 빈 문장이다(판정은 빈 문장을 error 로 본다)."""
    app = _load(monkeypatch, tmp_path, HELLO_API_URL="http://example.invalid/hello")

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{"message": null}'

    monkeypatch.setattr(app.urllib.request, "urlopen", lambda *a, **k: Resp())
    body = app.app.test_client().get("/").get_data(as_text=True)
    assert HELLO_LINE.search(body)[1] == ""


@mock_aws
def test_photo_upload_goes_under_images_and_target_health(monkeypatch, tmp_path):
    import io

    import boto3

    s3 = boto3.client("s3", region_name="ap-northeast-2")
    s3.create_bucket(Bucket="img-test", CreateBucketConfiguration={"LocationConstraint": "ap-northeast-2"})
    app = _load(monkeypatch, tmp_path, IMAGE_BUCKET="img-test", TARGET_GROUP_ARN="arn:aws:elasticloadbalancing:ap-northeast-2:000000000000:targetgroup/x/0")
    c = app.app.test_client()
    c.post("/entries", data={"name": "a", "msg": "사진", "image": (io.BytesIO(b"\x89PNG"), "Lunch.PNG")},
           content_type="multipart/form-data")
    keys = [o["Key"] for o in s3.list_objects_v2(Bucket="img-test")["Contents"]]
    assert len(keys) == 1 and keys[0].startswith("images/") and keys[0].endswith(".png")
    body = c.get("/?view=photo").get_data(as_text=True)
    assert "rev-thumb" in body and "서버 상태 읽기 실패" in body
