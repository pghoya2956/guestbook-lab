# 메뉴 2. 저장소를 데이터베이스로

쓰는 서비스: DynamoDB · 완료 기준: 글이 테이블에 쌓이고, 서버를 바꿔도 글이 남는다

## 바뀌는 구조

지금 글은 서버 디스크의 파일에 저장돼서 서버가 바뀌면 사라집니다(11단원에서 새 서버로 옮길 때 본 그 문제). 저장소를 DynamoDB 테이블로 옮기면 서버가 몇 대든, 바뀌든 같은 글을 봅니다.

## 만들 것

1. DynamoDB 테이블 만들기: 이름 `guestbook`, 파티션 키 `id` (문자열), 용량 모드 온디맨드
2. EC2 서버의 IAM 역할에 인라인 정책 추가: IAM → 역할 → `guestbook-ec2-role` → 권한 추가 → 인라인 정책 생성 → JSON 에 아래를 붙여 넣고, 정책 이름은 `guestbook-dynamodb` 처럼 정합니다. `계정ID` 는 콘솔 오른쪽 위에 보이는 12자리 숫자를 **하이픈 없이** 넣습니다(화면에는 `1234-5678-9012` 처럼 보여도 정책에는 하이픈을 뺀 숫자 열두 자리를 이어 씁니다).

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["dynamodb:Scan", "dynamodb:PutItem"],
    "Resource": "arn:aws:dynamodb:ap-northeast-2:계정ID:table/guestbook"
  }]
}
```

3. 로드 밸런서 뒤 서버 **두 대 모두** 같은 일을 합니다. 서버마다 Session Manager 로 접속해 `sudo nano /opt/guestbook/config.env` 로 열어 `STORAGE=dynamodb` 로 바꾸고 `sudo systemctl restart guestbook`

한 대만 바꾸면 새로고침할 때마다 `저장소: file` 과 `저장소: dynamodb` 가 번갈아 나오고, 쓴 글이 어느 서버로 갔는지에 따라 보였다 안 보였다 합니다.

손으로 고친 `config.env` 는 그 서버에만 남습니다. 오토 스케일링이 서버를 새로 만들면(서버 교체, 서버 늘리기) 새 서버는 다시 `file` 로 뜹니다. 모든 서버가 처음부터 DynamoDB 를 쓰게 하려면 메뉴 6 의 도전처럼 시작 템플릿 새 버전의 사용자 데이터에 `sed -i 's/^STORAGE=.*/STORAGE=dynamodb/' /opt/guestbook/config.env` 를 넣고 오토 스케일링 그룹의 인스턴스 새로 고침을 실행합니다.

## 확인

새 탭에 `http://로드 밸런서 DNS 이름` 을 열면 `저장소: dynamodb` 가 보이고, 글을 쓰면 DynamoDB 콘솔의 항목 탐색에 나타납니다. 로드 밸런서 뒤 서버들이 모두 같은 글을 보여 주는지 새로고침으로 확인합니다. 「보안 연결을 지원하지 않습니다」 경고가 뜨면 「사이트로 이동」을 누릅니다.

## 막히면

- 새로고침마다 저장소가 `file` 과 `dynamodb` 로 바뀜: 3번을 한 서버에만 했습니다. 나머지 서버도 바꿉니다.
- 역할 화면의 `access-analyzer:ListPolicyGenerations에 대한 액세스 거부됨` 빨간 상자: 이 메뉴에서 쓰지 않는 「정책 생성」 기능의 권한 오류라 무시해도 됩니다.

- 페이지가 500: `sudo journalctl -u guestbook -n 30` 에서 `AccessDeniedException` 이면 정책, `ResourceNotFoundException` 이면 테이블 이름을 봅니다.
