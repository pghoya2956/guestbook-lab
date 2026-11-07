import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE", "file")
    monkeypatch.setenv("DATA_FILE", str(tmp_path / "entries.json"))
    monkeypatch.setenv("GUESTBOOK_TITLE", "테스트 방명록")
    for m in ("app", "storage"):
        sys.modules.pop(m, None)
    app = importlib.import_module("app")
    app.app.config["TESTING"] = True
    return app.app.test_client()


def test_index_shows_title_host_and_storage(client):
    r = client.get("/")
    body = r.get_data(as_text=True)
    assert r.status_code == 200
    assert "테스트 방명록" in body
    assert "저장소: <b>file</b>" in body


def test_post_entry_then_listed(client):
    r = client.post("/entries", data={"name": "민수", "msg": "안녕"})
    assert r.status_code == 302
    body = client.get("/").get_data(as_text=True)
    assert "민수" in body and "안녕" in body


def test_empty_message_is_ignored(client):
    client.post("/entries", data={"name": "민수", "msg": "  "})
    assert "아직 글이 없습니다" in client.get("/").get_data(as_text=True)


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.get_json()["status"] == "ok"


def test_error_returns_500(client):
    assert client.get("/error").status_code == 500


def test_load_is_capped(client):
    r = client.get("/load?ms=5000")
    assert r.status_code == 200 and r.get_json()["ms"] == 1000


def test_hello_lambda_handler():
    sys.path.insert(0, str(ROOT / "lambda" / "hello"))
    mod = importlib.import_module("lambda_function")
    out = mod.lambda_handler({}, None)
    assert out["statusCode"] == 200 and "message" in out["body"]


@pytest.mark.parametrize("region", ["ap-northeast-2", "us-west-2"])
def test_image_url_uses_regional_s3_host(tmp_path, monkeypatch, region):
    """사진 주소는 리전 주소로 서명한다. 전역 주소(버킷.s3.amazonaws.com)는 새로 만든 버킷에서 한동안 us-east-1 로
    풀려 서울 서명이 거부됐다(2026-11-07 리허설, 403 SignatureDoesNotMatch / 400 AuthorizationQueryParametersError)."""
    monkeypatch.setenv("STORAGE", "file")
    monkeypatch.setenv("DATA_FILE", str(tmp_path / "entries.json"))
    monkeypatch.setenv("IMAGE_BUCKET", "guestbook-img-s01-1")
    monkeypatch.setenv("AWS_REGION", region)
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    for k in ("AWS_PROFILE", "AWS_ENDPOINT_URL", "AWS_ENDPOINT_URL_S3"):
        monkeypatch.delenv(k, raising=False)
    for m in ("app", "storage"):
        sys.modules.pop(m, None)
    app = importlib.import_module("app")
    url = app.image_url("images/a.png")
    assert url.split("/")[2] == f"guestbook-img-s01-1.s3.{region}.amazonaws.com"
    assert url.split("?")[0].endswith("/images/a.png")
    assert f"{region}%2Fs3%2Faws4_request" in url and "X-Amz-Expires=3600" in url
