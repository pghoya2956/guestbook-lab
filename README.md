# guestbook-lab

「AWS 클라우드 입문」 실습에서 이틀 동안 키워 가는 방명록 앱입니다. 앱 코드는 거의 바꾸지 않고, 앱이 사는 곳(서버, 네트워크, 저장소, 배포 방식)을 바꿔 가며 AWS를 배웁니다.

## 서버에 올리기

Amazon Linux 2023 서버에서 root 로 실행합니다. EC2 사용자 데이터에 넣으면 서버가 켜질 때 자동으로 실행됩니다.

```bash
curl -s https://raw.githubusercontent.com/pghoya2956/guestbook-lab/main/deploy/user-data.sh | sudo bash
```

앱은 80 포트로 뜹니다. 설정은 `/opt/guestbook/config.env` 이고, 바꾼 뒤에는 `sudo systemctl restart guestbook` 합니다. 설정 항목은 `config.env.example` 에 설명이 있습니다.

## 주소

| 주소 | 쓰는 곳 |
|---|---|
| `/` | 방명록. 맨 위에 응답한 서버 이름과 저장소 종류가 보입니다 |
| `/health` | 로드 밸런서 상태 검사 |
| `/load?ms=200` | 부하 실습. 요청마다 CPU 를 지정한 시간만큼 씁니다(최대 1000) |
| `/error` | 관측 실습. 일부러 500 오류를 냅니다 |

## 폴더

| 위치 | 내용 |
|---|---|
| `deploy/user-data.sh` | 서버를 켜자마자 앱을 띄우는 대본 |
| `guestbook.service` | 재부팅해도 앱이 살아 있게 하는 systemd 설정 |
| `static/` | S3 정적 웹사이트 실습 파일과 공지 `notice.txt` |
| `lambda/hello/` | 오늘의 한마디 Lambda 함수 |
| `lambda/api/` | DynamoDB 를 쓰는 서버리스 방명록 API |
| `Dockerfile`, `deploy/deploy.sh` | 컨테이너 이미지와 ECS 배포 |
| `.github/workflows/deploy.yml` | push 하면 ECS 로 배포(저장소 변수 `AWS_ROLE_ARN` 필요) |
| `terraform/setup-terraform.sh` | CloudShell 에 Terraform 설치 |
| `terraform/step1`, `step2` | Terraform 실습 1단계와 정답 |
| `docs/menu/` | 미니 프로젝트 개선 메뉴 안내 |

## 내 컴퓨터에서 실행

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
PORT=8080 DATA_FILE=data/entries.json .venv/bin/python app.py
```
