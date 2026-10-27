import importlib
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
from moto import mock_aws

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _load(monkeypatch, **env):
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("AWS_DEFAULT_REGION", "ap-northeast-2")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    for m in ("app", "storage"):
        sys.modules.pop(m, None)
    return importlib.import_module("app")


def test_health_reports_storage_and_notice(monkeypatch, tmp_path):
    app = _load(monkeypatch, STORAGE="file", DATA_FILE=str(tmp_path / "e.json"), NOTICE_BUCKET="b")
    body = app.app.test_client().get("/health").get_json()
    assert body["storage"] == "file" and body["notice"] is True and body["host"]


@mock_aws
def test_dynamodb_store_round_trip(monkeypatch):
    import boto3

    boto3.client("dynamodb", region_name="ap-northeast-2").create_table(
        TableName="guestbook",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    app = _load(monkeypatch, STORAGE="dynamodb", DYNAMODB_TABLE="guestbook")
    c = app.app.test_client()
    c.post("/entries", data={"name": "민수", "msg": "다이나모"})
    assert "다이나모" in c.get("/").get_data(as_text=True)
    assert c.get("/health").get_json()["storage"] == "dynamodb"


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture()
def mysql_port():
    if not shutil.which("docker") or subprocess.run(["docker", "info"], capture_output=True).returncode:
        pytest.skip("docker 없음")
    port = _free_port()
    name = f"gb-mysql-{port}"
    subprocess.run(
        ["docker", "run", "-d", "--rm", "--name", name, "-p", f"127.0.0.1:{port}:3306",
         "-e", "MYSQL_ROOT_PASSWORD=pw", "-e", "MYSQL_DATABASE=guestbook", "mysql:8.4"],
        check=True, capture_output=True,
    )
    try:
        import pymysql

        for _ in range(90):
            try:
                pymysql.connect(host="127.0.0.1", port=port, user="root", password="pw", database="guestbook").close()
                break
            except Exception:
                time.sleep(1)
        else:
            pytest.fail("mysql 기동 실패")
        yield port
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)


@mock_aws
def test_mysql_store_reads_params_and_round_trips(monkeypatch, mysql_port):
    import boto3

    ssm = boto3.client("ssm", region_name="ap-northeast-2")
    ssm.put_parameter(Name="/guestbook/db/host", Type="String", Value="127.0.0.1")
    ssm.put_parameter(Name="/guestbook/db/password", Type="SecureString", Value="pw")
    app = _load(monkeypatch, STORAGE="mysql", DB_USER="root", DB_PORT=str(mysql_port))
    c = app.app.test_client()
    c.post("/entries", data={"name": "지민", "msg": "마이에스큐엘"})
    assert "마이에스큐엘" in c.get("/").get_data(as_text=True)
    assert c.get("/health").get_json()["storage"] == "mysql"
