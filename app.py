"""AWS 클라우드 입문 실습용 방명록 앱.

설정은 환경 변수로 받는다. 서버에서는 config.env 를 systemd 가 읽어 넣는다.
"""
import hashlib
import json
import os
import random
import socket
import time
import urllib.request
import uuid
from pathlib import Path

from flask import Flask, abort, redirect, render_template, request, url_for

import storage

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

TITLE = os.environ.get("GUESTBOOK_TITLE", "우리 반 방명록")
INTRO = os.environ.get("GUESTBOOK_INTRO", "이름과 한마디를 남겨 주세요.")
NOTICE_BUCKET = os.environ.get("NOTICE_BUCKET", "")
IMAGE_BUCKET = os.environ.get("IMAGE_BUCKET", "")
HELLO_API_URL = os.environ.get("HELLO_API_URL", "")
AWS_REGION = os.environ.get("AWS_REGION", "ap-northeast-2")

LOCAL_HELLO = ["오늘도 화이팅", "커밋은 자주", "정리는 실력", "오류 메시지가 단서"]

store = storage.from_env()


def read_notice():
    """S3 의 notice.txt 를 요청마다 읽는다. 버킷을 안 정했거나 실패하면 빈 값."""
    if not NOTICE_BUCKET:
        return ""
    try:
        import boto3

        s3 = boto3.client("s3", region_name=AWS_REGION)
        obj = s3.get_object(Bucket=NOTICE_BUCKET, Key="notice.txt")
        return obj["Body"].read().decode("utf-8").strip()
    except Exception as e:  # 실습에서 권한·버킷 오류를 화면에 보여 준다
        return f"(공지를 읽지 못했습니다: {type(e).__name__})"


def hello_message():
    """HELLO_API_URL 이 있으면 Lambda 에서, 없으면 앱 안 목록에서 고른다."""
    if HELLO_API_URL:
        try:
            with urllib.request.urlopen(HELLO_API_URL, timeout=3) as r:
                return json.loads(r.read().decode("utf-8")).get("message", "")
        except Exception as e:
            return f"(한마디 API 오류: {type(e).__name__})"
    return random.choice(LOCAL_HELLO)


def image_url(key):
    if not (IMAGE_BUCKET and key):
        return ""
    import boto3

    s3 = boto3.client("s3", region_name=AWS_REGION)
    return s3.generate_presigned_url(
        "get_object", Params={"Bucket": IMAGE_BUCKET, "Key": key}, ExpiresIn=3600
    )


@app.get("/")
def index():
    entries = store.list(limit=50)
    for e in entries:
        e["image_url"] = image_url(e.get("image_key", ""))
    return render_template(
        "index.html",
        title=TITLE,
        intro=INTRO,
        notice=read_notice(),
        hello=hello_message(),
        entries=entries,
        host=socket.gethostname(),
        storage=store.name,
        image_enabled=bool(IMAGE_BUCKET),
    )


@app.post("/entries")
def add_entry():
    name = (request.form.get("name") or "익명").strip()[:30]
    msg = (request.form.get("msg") or "").strip()[:300]
    if not msg:
        return redirect(url_for("index"))
    image_key = ""
    f = request.files.get("image")
    if IMAGE_BUCKET and f and f.filename:
        import boto3

        image_key = f"images/{uuid.uuid4()}{Path(f.filename).suffix.lower()[:5]}"
        boto3.client("s3", region_name=AWS_REGION).upload_fileobj(
            f, IMAGE_BUCKET, image_key, ExtraArgs={"ContentType": f.mimetype}
        )
    store.add({"name": name, "msg": msg, "image_key": image_key})
    return redirect(url_for("index"))


@app.get("/health")
def health():
    """로드 밸런서 상태 검사용. 앱이 살아 있으면 200."""
    return {
        "status": "ok",
        "host": socket.gethostname(),
        "storage": store.name,
        "notice": bool(NOTICE_BUCKET),
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
