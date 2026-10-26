#!/bin/bash
# EC2 사용자 데이터. 서버가 처음 켜질 때 root 로 한 번 실행된다(1학년 14단원, 2학년 3단원).
# 실패하면 서버에서 /var/log/cloud-init-output.log 를 본다.
set -euxo pipefail

dnf install -y git python3.11
git clone https://github.com/pghoya2956/guestbook-lab.git /opt/guestbook
cd /opt/guestbook
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp config.env.example config.env
mkdir -p /var/lib/guestbook
cp guestbook.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now guestbook
