"""테스트 공용 준비물. docker 가 있으면 mysql:8.4 컨테이너를 띄운다."""
import shutil
import socket
import subprocess
import time

import pytest


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
