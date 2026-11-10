---
title: "메뉴 1. 방명록에 이미지 첨부"
sidebar:
  label: "1. 이미지 첨부"
  order: 1
---

쓰는 서비스: S3, IAM 역할

완료 기준: 올린 이미지가 방명록에 보인다

## 바뀌는 구조

방명록 서버가 사진을 자기 디스크가 아니라 S3 버킷에 저장하고, 페이지에는 잠깐만 유효한 주소(미리 서명된 URL)로 보여 줍니다. 버킷은 공개하지 않습니다.

## 만들 것

1. S3 버킷 하나 만들기. 이름 예: `guestbook-img-좌석번호-숫자`. 퍼블릭 액세스 차단은 **켜 둔 채로** 둡니다. <a href="https://s3.console.aws.amazon.com/s3/bucket/create?region=ap-northeast-2" target="_blank" rel="noopener">콘솔 열기 ↗</a>
2. EC2 서버에 붙은 IAM 역할에 인라인 정책 추가: <a href="https://console.aws.amazon.com/iam/home#/roles" target="_blank" rel="noopener">콘솔 열기 ↗</a>

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

3. 로드 밸런서 뒤 서버 **두 대 모두** 같은 일을 합니다. 서버마다 Session Manager 로 접속해 `sudo nano /opt/guestbook/config.env` 로 열어 `IMAGE_BUCKET=버킷이름` 을 적고 `sudo systemctl restart guestbook` <a href="https://ap-northeast-2.console.aws.amazon.com/ec2/home?region=ap-northeast-2#Instances:" target="_blank" rel="noopener">콘솔 열기 ↗</a>

한 대만 바꾸면 새로고침할 때마다 파일 선택 칸이 보였다 안 보였다 하고, 올린 글이 설정 없는 서버로 가면 사진 없이 저장됩니다.

## 확인

글을 쓸 때 파일 선택 칸이 생기고, 사진을 올리면 글 아래에 보입니다. S3 콘솔의 `images/` 아래에 파일이 생겼는지도 봅니다. <a href="https://s3.console.aws.amazon.com/s3/buckets?region=ap-northeast-2" target="_blank" rel="noopener">콘솔 열기 ↗</a>

## 막히면

- 업로드할 때 `AccessDenied`: 정책의 버킷 이름과 `images/*` 경로를 확인합니다.
- 새로고침마다 파일 선택 칸이 보였다 사라짐: 3번을 한 서버에만 했습니다. 나머지 서버도 바꿉니다.
- 오토 스케일링 서버에 적용하려면 시작 템플릿의 사용자 데이터 끝에 `echo IMAGE_BUCKET=버킷이름 >> /opt/guestbook/config.env` 와 `systemctl restart guestbook` 을 더하고 인스턴스를 새로 고칩니다. <a href="https://ap-northeast-2.console.aws.amazon.com/ec2/home?region=ap-northeast-2#LaunchTemplates:" target="_blank" rel="noopener">시작 템플릿 ↗</a> <a href="https://ap-northeast-2.console.aws.amazon.com/ec2/home?region=ap-northeast-2#AutoScalingGroups:" target="_blank" rel="noopener">오토 스케일링 그룹 ↗</a>
