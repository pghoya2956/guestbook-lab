---
title: "메뉴 3. 기능 하나를 서버리스로 분리"
sidebar:
  label: "3. 서버리스 분리"
  order: 3
---

쓰는 서비스: Lambda, API Gateway

완료 기준: 분리한 주소가 응답하고 방명록이 그 응답을 보여 준다

## 바뀌는 구조

「오늘의 한마디」를 서버 안에서 고르지 않고 Lambda 함수가 골라 줍니다. 방명록 서버는 함수의 주소만 부릅니다.

## 만들 것

1. [13단원](/guestbook-lab/u13/)에서 만든 `guestbook-hello` 함수가 있으면 그대로 씁니다. 없으면 `lambda/hello/lambda_function.py`(<a href="https://github.com/pghoya2956/guestbook-lab/blob/main/lambda/hello/lambda_function.py" target="_blank" rel="noopener">저장소에서 보기 ↗</a>) 로 만들고 API Gateway(HTTP API) 트리거를 붙입니다. <a href="https://ap-northeast-2.console.aws.amazon.com/lambda/home?region=ap-northeast-2#/functions" target="_blank" rel="noopener">콘솔 열기 ↗</a>
2. 함수의 메시지 목록을 내 문장으로 바꾸고 Deploy
3. 로드 밸런서 뒤 서버 **두 대 모두** 같은 일을 합니다. 서버마다 Session Manager 로 접속해 `sudo nano /opt/guestbook/config.env` 로 열어 `HELLO_API_URL=함수 API 주소` 를 적고 `sudo systemctl restart guestbook` <a href="https://ap-northeast-2.console.aws.amazon.com/ec2/home?region=ap-northeast-2#Instances:" target="_blank" rel="noopener">콘솔 열기 ↗</a>

한 대만 바꾸면 새로고침할 때마다 내 문장과 원래 문장이 번갈아 나옵니다.

## 확인

방명록 「오늘의 한마디」에 내가 넣은 문장이 나옵니다. 브라우저로 API 주소를 직접 열어도 같은 형식의 응답이 옵니다.

## 막히면

- 한마디 자리에 `한마디 API 오류`: 주소 끝의 경로까지 정확히 넣었는지, 브라우저로 열었을 때 응답이 오는지 확인합니다.
