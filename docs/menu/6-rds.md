# 메뉴 6(심화). 저장소를 MySQL 데이터베이스로

쓰는 서비스: RDS, Parameter Store, 보안 그룹 · 완료 기준: 페이지에 `저장소: mysql` 이 보이고 글이 DB 에 쌓인다

2학년과 빨리 끝낸 학생용입니다. DB 만들기에 10분 넘게 걸리니 **1번부터 바로 시작**하고 기다리는 동안 나머지를 합니다.

## 바뀌는 구조

글을 서버 디스크 대신 RDS MySQL 에 저장합니다. DB 는 인터넷에 열지 않고, 방명록 서버의 보안 그룹에서 오는 연결만 받습니다. DB 주소와 비밀번호는 코드나 설정 파일이 아니라 Parameter Store 에 두고 앱이 실행될 때 읽어 갑니다.

## 만들 것

1. RDS → 데이터베이스 생성
   - 표준 생성, 엔진 MySQL, 템플릿 **프리 티어**
   - DB 인스턴스 식별자 `guestbook-db`, 마스터 사용자 이름 `admin`, 자격 증명 관리는 **자체 관리**, 비밀번호 직접 입력(메모해 둡니다)
   - 인스턴스 클래스 `db.t3.micro` 또는 `db.t4g.micro`, 스토리지 20 GiB, 스토리지 자동 조정 **끄기**
   - 연결: VPC `guestbook-vpc`, 퍼블릭 액세스 **아니요**, 새 VPC 보안 그룹 `guestbook-db`
   - 추가 구성: 초기 데이터베이스 이름 `guestbook`, 자동 백업 **끄기**
2. EC2 → 보안 그룹 → `guestbook-db` → 인바운드 규칙 편집: 유형 MYSQL/Aurora(3306), 소스는 **방명록 서버의 보안 그룹**(IP 가 아니라 보안 그룹을 고릅니다). 처음 생긴 규칙(내 IP)은 지웁니다.
3. Systems Manager → Parameter Store → 파라미터 두 개 만들기
   - `/guestbook/db/host`: 유형 String, 값은 RDS 의 엔드포인트(생성이 끝나면 연결 및 보안 탭에 나옵니다)
   - `/guestbook/db/password`: 유형 **SecureString**, 값은 1번 비밀번호
4. 방명록 서버의 IAM 역할에 인라인 정책 추가:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "ssm:GetParameter",
    "Resource": "arn:aws:ssm:ap-northeast-2:계정ID:parameter/guestbook/db/*"
  }]
}
```

5. 서버 한 대에 Session Manager 로 접속해 `config.env` 의 `STORAGE=mysql` 로 바꾸고 `sudo systemctl restart guestbook`

## 확인

그 서버의 퍼블릭 IP 로 방명록을 열면 `저장소: mysql` 이 보입니다. 글을 쓰고 서비스를 재시작해도 글이 남아 있으면 완료입니다.

도전: 로드 밸런서 뒤 모든 서버가 MySQL 을 쓰게 하려면 시작 템플릿 새 버전의 사용자 데이터에 `sed -i 's/^STORAGE=.*/STORAGE=mysql/' /opt/guestbook/config.env` 를 넣고 오토 스케일링 그룹의 인스턴스 새로 고침을 실행합니다.

## 막히면

- 페이지가 500: `journalctl -u guestbook -n 30` 을 봅니다.
  - `ParameterNotFound`: 파라미터 이름 오타. `/guestbook/db/host` 처럼 앞에 `/` 가 있어야 합니다
  - `AccessDeniedException`: 4번 정책의 계정 ID 나 경로
  - `Can't connect to MySQL server` 또는 시간 초과: 2번 보안 그룹 규칙의 소스가 방명록 서버의 보안 그룹인지
  - `Access denied for user`: 3번 비밀번호 값
- DB 생성이 거부: 클래스나 스토리지 크기가 수업 계정에서 허용한 값(`db.t3.micro`, `db.t4g.micro`, 20 GiB)을 넘었는지 봅니다.
- 수업이 끝나면 DB 를 꼭 삭제합니다(최종 스냅샷 만들지 않음). 켜져 있는 동안 시간당 요금이 붙습니다.
