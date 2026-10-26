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
