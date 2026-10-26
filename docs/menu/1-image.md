# 메뉴 1. 방명록에 이미지 첨부

쓰는 서비스: S3, IAM 역할 · 완료 기준: 올린 이미지가 방명록에 보인다

## 바뀌는 구조

방명록 서버가 사진을 자기 디스크가 아니라 S3 버킷에 저장하고, 페이지에는 잠깐만 유효한 주소(미리 서명된 URL)로 보여 줍니다. 버킷은 공개하지 않습니다.

## 만들 것

1. S3 버킷 하나 만들기. 이름 예: `guestbook-img-좌석번호-숫자`. 퍼블릭 액세스 차단은 **켜 둔 채로** 둡니다.
2. EC2 서버에 붙은 IAM 역할에 인라인 정책 추가:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["s3:PutObject", "s3:GetObject"],
    "Resource": "arn:aws:s3:::버킷이름/images/*"
  }]
}
```

3. 서버의 `/opt/guestbook/config.env` 에 `IMAGE_BUCKET=버킷이름` 을 적고 `sudo systemctl restart guestbook`

## 확인

글을 쓸 때 파일 선택 칸이 생기고, 사진을 올리면 글 아래에 보입니다. S3 콘솔의 `images/` 아래에 파일이 생겼는지도 봅니다.

## 막히면

- 업로드할 때 `AccessDenied`: 정책의 버킷 이름과 `images/*` 경로를 확인합니다.
- 오토 스케일링 서버에 적용하려면 시작 템플릿의 사용자 데이터 끝에 `echo IMAGE_BUCKET=버킷이름 >> /opt/guestbook/config.env` 와 `systemctl restart guestbook` 을 더하고 인스턴스를 새로 고칩니다.
