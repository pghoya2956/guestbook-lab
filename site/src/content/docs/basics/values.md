---
title: 리전과 되는 값
description: 서울 리전, 수업 계정에서 되는 값, 수업에서 쓰는 이름
sidebar:
  order: 1
---

## 리전은 서울

콘솔 오른쪽 위 리전이 **서울**(ap-northeast-2)인지 먼저 봅니다. 수업 계정은 서울 밖을 막아 두어서 다른 리전에서는 목록이 비거나 빨간 권한 오류가 뜹니다.

## 수업 계정에서 되는 값

이 밖의 값을 고르면 권한 오류로 거부됩니다.

| 무엇 | 되는 값 |
|---|---|
| EC2 인스턴스 유형 | `t3.micro`, `t3.small`. 서울의 기본값 `t2.micro` 는 거부됩니다 |
| EBS 볼륨 | 하나에 30GB 이하 |
| RDS | 엔진 MySQL, 클래스 `db.t3.micro` 또는 `db.t4g.micro`, 단일 AZ, 스토리지 20GB 이하. Aurora 는 만들 수 없습니다 |
| NAT 게이트웨이 | 만들 수 없습니다 |
| 액세스 키 | 만들 수 없습니다. 서버에서는 IAM 역할을, 브라우저에서는 CloudShell 을 씁니다 |
| 비싼 서비스 | SageMaker, Bedrock, EKS 같은 서비스는 막혀 있습니다 |

## 수업에서 쓰는 이름

| 단원 | 이름 |
|---|---|
| [4단원](/guestbook-lab/u4/) | 역할 `guestbook-ec2-role`, 서버 `guestbook-1` |
| [7단원](/guestbook-lab/u7/) | 버킷 `guestbook-좌석번호-아무숫자` (예: `guestbook-s01-1104`) |
| [9단원](/guestbook-lab/u9/) | 공지 버킷 `guestbook-notice-좌석번호-숫자` |
| [10단원](/guestbook-lab/u10/) | `guestbook-vpc`, 서브넷 `public-a`(2a)와 `public-c`(2c), `guestbook-igw`, `guestbook-public-rt` |
| [11단원](/guestbook-lab/u11/) | 시작 템플릿 `guestbook-lt`, 보안 그룹 `guestbook-web`, 서버 `guestbook-2` |
| [12단원](/guestbook-lab/u12/) | `guestbook-tg`, `guestbook-alb`, `guestbook-alb-sg`, `guestbook-asg` |
| [13단원](/guestbook-lab/u13/) | 함수 `guestbook-hello` |
