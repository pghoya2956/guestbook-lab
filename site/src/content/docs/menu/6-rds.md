---
title: "메뉴 6(심화). 저장소를 MySQL 데이터베이스로"
sidebar:
  label: "6. MySQL (심화)"
  order: 6
---

쓰는 서비스: RDS, Parameter Store, 보안 그룹

완료 기준: 페이지에 `저장소: mysql` 이 보이고 글이 DB 에 쌓인다

2학년과 빨리 끝낸 학생용입니다. DB 만들기에 약 5분 걸리니 **1번부터 바로 시작**하고 기다리는 동안 나머지를 합니다.

## 바뀌는 구조

글을 서버 디스크 대신 RDS MySQL 에 저장합니다. DB 는 인터넷에 열지 않고, 방명록 서버의 보안 그룹에서 오는 연결만 받습니다. DB 주소와 비밀번호는 코드나 설정 파일이 아니라 Parameter Store 에 두고 앱이 실행될 때 읽어 갑니다.

## 만들 것

1. RDS → 데이터베이스 생성 <a href="https://ap-northeast-2.console.aws.amazon.com/rds/home?region=ap-northeast-2#launch-dbinstance:" target="_blank" rel="noopener">콘솔 열기 ↗</a>
   - **전체 구성**, 엔진 **MySQL**(처음에는 Aurora PostgreSQL 이 골라져 있으니 바꿉니다), 템플릿 **샌드박스**
   - DB 인스턴스 식별자 `guestbook-db`, 마스터 사용자 이름 `admin`, 자격 증명 관리는 **자체 관리**(MySQL 을 고른 직후에는 Secrets Manager 로 골라져 있고 샌드박스를 고르면 자체 관리로 바뀝니다. 엔진, 템플릿 순서로 고른 뒤 다시 확인합니다), 비밀번호 직접 입력(메모해 둡니다)
   - 인스턴스 클래스 `db.t3.micro` 또는 `db.t4g.micro`, 스토리지 20 GiB(샌드박스를 고르면 `db.t4g.micro`, 20 GiB 로 채워집니다). **추가 스토리지 구성**을 펼쳐 스토리지 자동 조정 **끄기**(기본으로 켜져 있습니다)
   - 연결: VPC `guestbook-vpc`(기본값은 Default VPC 라 바꿔야 합니다), 퍼블릭 액세스 **아니요**, 새 VPC 보안 그룹 `guestbook-db`
   - 맨 아래 **추가 구성**을 펼쳐 초기 데이터베이스 이름 `guestbook`, 자동 백업 **끄기**(기본으로 켜져 있습니다)
   - 데이터베이스 생성을 누른 뒤 Chrome 이 비밀번호를 저장할지 물으면 저장하지 않습니다(「사용 안함」). 공용 PC 에 DB 비밀번호가 남습니다.
2. EC2 → 보안 그룹 → `guestbook-db` → 인바운드 규칙 편집: 유형 MYSQL/Aurora(3306), 소스는 **방명록 서버의 보안 그룹**(11단원 시작 템플릿에서 만든 것. IP 가 아니라 보안 그룹을 고릅니다). 소스 칸에 그 보안 그룹 이름을 치면 목록에 나옵니다. 처음 생긴 규칙(내 IP)은 지웁니다. <a href="https://ap-northeast-2.console.aws.amazon.com/ec2/home?region=ap-northeast-2#SecurityGroups:" target="_blank" rel="noopener">콘솔 열기 ↗</a>
3. Systems Manager → Parameter Store → 파라미터 생성으로 두 개 만들기 <a href="https://ap-northeast-2.console.aws.amazon.com/systems-manager/parameters/?region=ap-northeast-2" target="_blank" rel="noopener">콘솔 열기 ↗</a>
   - `/guestbook/db/host`: 유형 String(문자열), 값은 RDS 의 엔드포인트(연결 및 보안 탭에 나옵니다) <a href="https://ap-northeast-2.console.aws.amazon.com/rds/home?region=ap-northeast-2#databases:" target="_blank" rel="noopener">RDS 열기 ↗</a>
   - `/guestbook/db/password`: 유형 **보안 문자열**(목록에서는 SecureString 으로 보입니다), 값은 1번 비밀번호
4. 방명록 서버의 IAM 역할에 인라인 정책 추가: <a href="https://console.aws.amazon.com/iam/home#/roles" target="_blank" rel="noopener">콘솔 열기 ↗</a>

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

5. 서버 한 대에 Session Manager 로 접속해 `sudo nano /opt/guestbook/config.env` 로 열어 `STORAGE=mysql` 로 바꾸고 `sudo systemctl restart guestbook` <a href="https://ap-northeast-2.console.aws.amazon.com/ec2/home?region=ap-northeast-2#Instances:" target="_blank" rel="noopener">콘솔 열기 ↗</a>

## 확인

새 탭에 `http://그 서버의 퍼블릭 IP` 로 방명록을 열면 `저장소: mysql` 이 보입니다(「보안 연결을 지원하지 않습니다」 경고가 뜨면 「사이트로 이동」). 글을 쓰고 서비스를 재시작해도 글이 남아 있으면 완료입니다.

도전: 로드 밸런서 뒤 모든 서버가 MySQL 을 쓰게 하려면 시작 템플릿 새 버전의 사용자 데이터에 `sed -i 's/^STORAGE=.*/STORAGE=mysql/' /opt/guestbook/config.env` 를 넣고 오토 스케일링 그룹의 인스턴스 새로 고침을 실행합니다. <a href="https://ap-northeast-2.console.aws.amazon.com/ec2/home?region=ap-northeast-2#LaunchTemplates:" target="_blank" rel="noopener">시작 템플릿 ↗</a> <a href="https://ap-northeast-2.console.aws.amazon.com/ec2/home?region=ap-northeast-2#AutoScalingGroups:" target="_blank" rel="noopener">오토 스케일링 그룹 ↗</a>

## 막히면

- 페이지가 500: `sudo journalctl -u guestbook -n 30` 을 봅니다.
  - `ParameterNotFound`: 파라미터 이름 오타. `/guestbook/db/host` 처럼 앞에 `/` 가 있어야 합니다
  - `AccessDeniedException`: 4번 정책의 계정 ID 나 경로
  - `Can't connect to MySQL server` 또는 시간 초과: 2번 보안 그룹 규칙의 소스가 방명록 서버의 보안 그룹인지
  - `Access denied for user`: 3번 비밀번호 값
- 파라미터를 만들자 「연결 생성 요청에 성공했습니다!」가 뜸: 번역이 어색한 안내일 뿐 파라미터는 만들어졌습니다. 목록에서 이름을 확인합니다.
- DB 생성이 거부: 클래스나 스토리지 크기가 수업 계정에서 허용한 값(`db.t3.micro`, `db.t4g.micro`, 20 GiB)을 넘었는지 봅니다.
- 수업이 끝나면 DB 를 꼭 삭제합니다. 켜져 있는 동안 시간당 요금이 붙습니다. 삭제 창의 「최종 스냅샷 생성」은 기본으로 켜져 있으니 끄고, 새로 나오는 인정 체크 상자에 체크한 뒤 `delete me` 를 입력합니다. 스냅샷을 남기면 그것도 요금이 붙습니다. <a href="https://ap-northeast-2.console.aws.amazon.com/rds/home?region=ap-northeast-2#databases:" target="_blank" rel="noopener">콘솔 열기 ↗</a>
