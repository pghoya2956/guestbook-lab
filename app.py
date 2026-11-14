"""AWS 클라우드 입문 실습용 급식 리뷰 앱 「오늘 급식」.

설정은 환경 변수로 받는다. 서버에서는 config.env 를 systemd 가 읽어 넣는다.
오늘 메뉴는 S3 의 notice.txt 에서, 급식실 한마디는 Lambda 에서, 리뷰는 STORAGE 저장소에서 온다.
"""
import hashlib
import json
import os
import random
import re
import socket
import time
import urllib.request
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from flask import Flask, abort, redirect, render_template, request, url_for

import storage

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

APP_VERSION = "2.0.0"
TITLE = os.environ.get("GUESTBOOK_TITLE", "오늘 급식")
INTRO = os.environ.get("GUESTBOOK_INTRO", "우리 반이 운영하는 급식 리뷰")
NOTICE_BUCKET = os.environ.get("NOTICE_BUCKET", "")
IMAGE_BUCKET = os.environ.get("IMAGE_BUCKET", "")
HELLO_API_URL = os.environ.get("HELLO_API_URL", "")
AWS_REGION = os.environ.get("AWS_REGION", "ap-northeast-2")
# 로드 밸런서 대상 그룹 ARN. 적으면 운영 띠에 「서버 2/2 정상」을 보인다(서버 역할에 elasticloadbalancing:DescribeTargetHealth 필요)
TARGET_GROUP_ARN = os.environ.get("TARGET_GROUP_ARN", "")
MEAL_NAME = os.environ.get("MEAL_NAME", "점심")

# 강사 진척 판정(13단원)이 화면의 한마디가 이 목록 밖이면 Lambda 에서 왔다고 본다. 바꾸면 판정 쪽 목록도 같이 고친다
LOCAL_HELLO = ["오늘도 화이팅", "커밋은 자주", "정리는 실력", "오류 메시지가 단서"]

KST = timezone(timedelta(hours=9))
WEEKDAYS = "월화수목금토일"
AVATAR_TINTS = ("#2E7D5B", "#2F5BEA", "#7A5C3E", "#56616B", "#5B4B8A", "#1F6B70")

store = storage.from_env()


def _quick_config():
    from botocore.config import Config

    # 로드 밸런서 상태 검사도 공지 읽기를 거친다. AWS 가 막혀도 오래 묶이지 않게 짧게 끊는다
    return Config(connect_timeout=2, read_timeout=2, retries={"max_attempts": 1})


def read_notice_status():
    """(상태, 공지 문장). 상태는 ok, missing(버킷을 안 정함), error(권한·버킷 오류). S3 의 notice.txt 를 요청마다 읽는다."""
    if not NOTICE_BUCKET:
        return "missing", ""
    try:
        import boto3

        s3 = boto3.client("s3", region_name=AWS_REGION, config=_quick_config())
        obj = s3.get_object(Bucket=NOTICE_BUCKET, Key="notice.txt")
        return "ok", obj["Body"].read().decode("utf-8").strip()
    except Exception as e:  # 실습에서 권한·버킷 오류를 화면에 보여 준다
        return "error", f"(공지를 읽지 못했습니다: {type(e).__name__})"


# notice.txt 메뉴 형식: 한 줄에 「칸|음식|알레르기 번호」. 칸은 밥, 국, 반찬(여러 줄), 후식, 열량.
# 메뉴 줄이 하나도 없으면 예전처럼 글 전체를 공지 문장으로 보인다. 메뉴 줄이 아닌 줄은 공지로 모은다
_SLOTS = {"밥": "rice", "국": "soup", "후식": "dessert", "열량": "kcal"}


def parse_menu(text):
    """notice.txt 글을 메뉴로 읽는다. 메뉴 줄이 없으면 None."""
    menu = {"rice": None, "soup": None, "sides": [], "dessert": None, "kcal": "", "notes": []}
    found = False
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        slot = parts[0]
        kind = _SLOTS.get(slot) or ("side" if re.fullmatch(r"반찬\s*\d*", slot) else None)
        if not kind or len(parts) < 2 or not parts[1]:
            menu["notes"].append(line)
            continue
        found = True
        if kind == "kcal":
            menu["kcal"] = parts[1][:10]
            continue
        dish = {"name": parts[1][:30], "allergy": (parts[2] if len(parts) > 2 else "")[:40]}
        if kind == "side" or menu[kind] is not None:
            menu["sides"].append(dish)
        else:
            menu[kind] = dish
    return menu if found else None


def hello_info():
    """(한마디, 출처, 걸린 ms). 출처는 lambda, local(앱 안 목록), error. HELLO_API_URL 이 있으면 Lambda 에서 받는다."""
    if HELLO_API_URL:
        start = time.perf_counter()
        try:
            with urllib.request.urlopen(HELLO_API_URL, timeout=3) as r:
                msg = json.loads(r.read().decode("utf-8")).get("message") or ""
            return msg, "lambda", round((time.perf_counter() - start) * 1000)
        except Exception as e:
            return f"(한마디 API 오류: {type(e).__name__})", "error", round((time.perf_counter() - start) * 1000)
    return random.choice(LOCAL_HELLO), "local", 0


def image_url(key):
    if not (IMAGE_BUCKET and key):
        return ""
    import boto3
    from botocore.config import Config

    # 가상 호스트 방식을 정해 주면 리전 주소(버킷.s3.<리전>.amazonaws.com)로 서명한다. 기본값은 전역 주소라
    # 새로 만든 버킷에서 한동안 us-east-1 로 풀려 서명이 거부되고 사진이 안 보인다
    s3 = boto3.client(
        "s3",
        region_name=AWS_REGION,
        config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
    )
    return s3.generate_presigned_url(
        "get_object", Params={"Bucket": IMAGE_BUCKET, "Key": key}, ExpiresIn=3600
    )


_az_cache = {}


def _on_ec2():
    """EC2 에서만 인스턴스 메타데이터를 부른다. 내 컴퓨터에서 부르면 시간만 버린다."""
    for p, test in (("/sys/devices/virtual/dmi/id/board_asset_tag", lambda s: s.startswith("i-")),
                    ("/sys/hypervisor/uuid", lambda s: s.lower().startswith("ec2"))):
        try:
            if test(Path(p).read_text().strip()):
                return True
        except OSError:
            pass
    return False


def availability_zone():
    """이 서버의 가용 영역 짧은 이름(예: 2a). EC2 가 아니거나 못 읽으면 빈 값. 한 번만 읽는다."""
    if "az" not in _az_cache:
        az = ""
        if _on_ec2():
            try:
                base = "http://169.254.169.254/latest"
                tok = urllib.request.Request(f"{base}/api/token", method="PUT",
                                             headers={"X-aws-ec2-metadata-token-ttl-seconds": "60"})
                with urllib.request.urlopen(tok, timeout=1) as r:
                    token = r.read().decode()
                req = urllib.request.Request(f"{base}/meta-data/placement/availability-zone",
                                             headers={"X-aws-ec2-metadata-token": token})
                with urllib.request.urlopen(req, timeout=1) as r:
                    az = r.read().decode().strip()
            except Exception:
                az = ""
        _az_cache["az"] = az.rsplit("-", 1)[-1] if az else ""
    return _az_cache["az"]


_tg_cache = {"at": 0.0, "val": None}


def target_health():
    """대상 그룹의 정상 서버 수. TARGET_GROUP_ARN 이 없으면 None. 10초 동안 같은 값을 쓴다."""
    if not TARGET_GROUP_ARN:
        return None
    if time.time() - _tg_cache["at"] < 10:
        return _tg_cache["val"]
    try:
        import boto3

        elb = boto3.client("elbv2", region_name=AWS_REGION, config=_quick_config())
        ds = elb.describe_target_health(TargetGroupArn=TARGET_GROUP_ARN)["TargetHealthDescriptions"]
        val = {"healthy": sum(d["TargetHealth"]["State"] == "healthy" for d in ds), "total": len(ds), "error": ""}
    except Exception as e:
        val = {"healthy": 0, "total": 0, "error": type(e).__name__}
    _tg_cache.update(at=time.time(), val=val)
    return val


def today_kst():
    return datetime.now(KST).date()


def day_label(d, short=False):
    wd = WEEKDAYS[d.weekday()]
    return f"{d.month}월 {d.day}일 {wd}" if short else f"{d.month}월 {d.day}일 {wd}요일"


def ago(ts, now):
    """리뷰를 쓴 때를 사람이 읽는 말로."""
    sec = max(0, int(now - ts))
    when = datetime.fromtimestamp(ts, KST)
    if sec < 60:
        return "방금"
    if sec < 3600:
        return f"{sec // 60}분 전"
    today = datetime.fromtimestamp(now, KST).date()
    if when.date() == today:
        return f"{sec // 3600}시간 전"
    if when.date() == today - timedelta(days=1):
        return f"어제 {when:%H:%M}"
    return f"{when.month}월 {when.day}일"


def avatar_tint(name):
    return AVATAR_TINTS[int(hashlib.md5(name.encode("utf-8")).hexdigest(), 16) % len(AVATAR_TINTS)]


def _parse_day(s):
    """?day=YYYY-MM-DD. 오늘이거나 그 뒤, 형식이 틀리면 None(오늘 보기)."""
    try:
        d = date.fromisoformat(s or "")
    except ValueError:
        return None
    return d if d < today_kst() else None


def _menu_view(notice_state, notice_text, reviews):
    """오늘 메뉴 영역에 쓸 값. 칸마다 오늘 쓴 리뷰 수를 세고 가장 많은 칸을 표시한다."""
    menu = parse_menu(notice_text) if notice_state == "ok" else None
    if not menu:
        return None, []
    counts = {}
    today = today_kst()
    for r in reviews:
        # 김치처럼 매일 나오는 반찬이 지난 리뷰로 쌓이지 않게 오늘 리뷰만 센다
        if r["dish"] and datetime.fromtimestamp(r["ts"], KST).date() == today:
            counts[r["dish"]] = counts.get(r["dish"], 0) + 1
    dishes = [d for d in [*menu["sides"], menu["rice"], menu["soup"], menu["dessert"]] if d]
    for d in dishes:
        d["reviews"] = counts.get(d["name"], 0)
    top = max((d["reviews"] for d in dishes), default=0)
    for d in dishes:
        d["top"] = top > 0 and d["reviews"] == top
    # 반찬 칸은 세 칸씩 한 줄이다. 모자라는 칸은 빈 칸으로 채워 식판 모양을 지킨다
    menu["empty_sides"] = max(3 - len(menu["sides"]), -len(menu["sides"]) % 3)
    return menu, [d["name"] for d in dishes]


@app.get("/")
def index():
    started = time.perf_counter()
    now = time.time()
    today = today_kst()
    day = _parse_day(request.args.get("day"))
    view = "photo" if request.args.get("view") == "photo" else "all"

    store_error = ""
    try:
        reviews = store.list(limit=200)
    except Exception as e:  # 저장소 권한·연결 오류. 화면에 오류 이름을 보이고 자세한 내용은 앱 기록(journalctl)에 남긴다
        app.logger.exception("리뷰 저장소를 읽지 못했습니다")
        store_error = type(e).__name__
        reviews = []

    notice_state, notice_text = read_notice_status()
    menu, dish_names = _menu_view(notice_state, notice_text, reviews)
    hello, hello_source, hello_ms = hello_info()

    if day:
        reviews = [r for r in reviews if datetime.fromtimestamp(r["ts"], KST).date() == day]
    reviews = reviews[:50]
    for r in reviews:
        r["image_url"] = image_url(r["image_key"])
        r["ago"] = ago(r["ts"], now)
        r["tint"] = avatar_tint(r["name"])
    photos = [r for r in reviews if r["image_url"]]
    shown = photos if view == "photo" else reviews

    shown_day = day or today
    nxt = shown_day + timedelta(days=1)
    return render_template(
        "index.html",
        title=TITLE,
        intro=INTRO,
        version=APP_VERSION,
        region=AWS_REGION,
        host=socket.gethostname(),
        az=availability_zone(),
        targets=target_health(),
        storage=store.name,
        store_error=store_error,
        notice_state=notice_state,
        notice=notice_text,
        menu=menu,
        dish_names=dish_names,
        read_at=datetime.now(KST).strftime("%H:%M"),
        hello=hello,
        hello_source=hello_source,
        hello_ms=hello_ms,
        reviews=shown,
        review_count=len(reviews),
        photos=photos,
        view=view,
        day=day,
        day_long=day_label(shown_day),
        day_short=day_label(shown_day, short=True),
        meal=MEAL_NAME,
        prev_day=(shown_day - timedelta(days=1)).isoformat(),
        next_day=None if not day else ("" if nxt >= today else nxt.isoformat()),
        image_enabled=bool(IMAGE_BUCKET),
        form_error=request.args.get("error") == "save",
        render_ms=round((time.perf_counter() - started) * 1000),
    )


@app.post("/entries")
def add_entry():
    name = (request.form.get("name") or "익명").strip()[:30] or "익명"
    msg = (request.form.get("msg") or "").strip()[:300]
    dish = (request.form.get("dish") or "").strip()[:30]
    if not msg:
        return redirect(url_for("index"))
    try:
        image_key = ""
        f = request.files.get("image")
        if IMAGE_BUCKET and f and f.filename:
            import boto3

            image_key = f"images/{uuid.uuid4()}{Path(f.filename).suffix.lower()[:5]}"
            boto3.client("s3", region_name=AWS_REGION).upload_fileobj(
                f, IMAGE_BUCKET, image_key, ExtraArgs={"ContentType": f.mimetype}
            )
        store.add({"name": name, "msg": msg, "image_key": image_key, "host": socket.gethostname(), "dish": dish})
    except Exception:  # 사진 버킷이나 저장소 권한 오류. 자세한 내용은 앱 기록(journalctl)에 남는다
        app.logger.exception("리뷰를 저장하지 못했습니다")
        return redirect(url_for("index", error="save") + "#write")
    return redirect(url_for("index") + "#reviews")


@app.get("/health")
def health():
    """로드 밸런서 상태 검사용. 앱이 살아 있으면 200."""
    return {
        "status": "ok",
        "host": socket.gethostname(),
        "storage": store.name,
        "notice": read_notice_status()[0],  # ok | missing | error (강사 관측이 9단원 판정에 쓴다)
    }


@app.get("/error")
def error():
    """관측 실습용. 일부러 500 을 낸다."""
    abort(500)


@app.get("/load")
def load():
    """부하 실습용. ms 만큼 CPU 를 쓴다(최대 1000ms)."""
    ms = min(max(int(request.args.get("ms", 200)), 0), 1000)
    end = time.perf_counter() + ms / 1000
    h = b"guestbook"
    n = 0
    while time.perf_counter() < end:
        h = hashlib.sha256(h).digest()
        n += 1
    return {"host": socket.gethostname(), "ms": ms, "rounds": n}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "80")))
