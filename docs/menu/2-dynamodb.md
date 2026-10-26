# 메뉴 2. 저장소를 데이터베이스로

쓰는 서비스: DynamoDB · 완료 기준: 글이 테이블에 쌓이고, 서버를 바꿔도 글이 남는다

## 바뀌는 구조

지금 글은 서버 디스크의 파일에 저장돼서 서버가 바뀌면 사라집니다(13단원에서 본 그 문제). 저장소를 DynamoDB 테이블로 옮기면 서버가 몇 대든, 바뀌든 같은 글을 봅니다.

## 만들 것

1. DynamoDB 테이블 만들기: 이름 `guestbook`, 파티션 키 `id` (문자열), 용량 모드 온디맨드
2. EC2 서버의 IAM 역할에 인라인 정책 추가:

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

3. `config.env` 에서 `STORAGE=dynamodb` 로 바꾸고 `sudo systemctl restart guestbook`

## 확인

페이지에 `저장소: dynamodb` 가 보이고, 글을 쓰면 DynamoDB 콘솔의 항목 탐색에 나타납니다. 로드 밸런서 뒤 서버들이 모두 같은 글을 보여 주는지 새로고침으로 확인합니다.

## 막히면

- 페이지가 500: `journalctl -u guestbook -n 30` 에서 `AccessDeniedException` 이면 정책, `ResourceNotFoundException` 이면 테이블 이름을 봅니다.
