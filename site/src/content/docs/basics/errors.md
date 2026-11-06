---
title: 오류 읽는 법
description: 권한 오류 문구 구분하기, http 주소가 안 열릴 때
sidebar:
  order: 2
---

## 권한 오류 읽는 법

빨간 오류 상자에서 아래 문구를 찾아보세요. 3단원에서 연습한 읽기입니다.

:::caution[`explicit deny in a service control policy`]
수업 계정이 막아 둔 일을 했습니다. 리전이 서울인지, [수업 계정에서 되는 값](/guestbook-lab/basics/values/) 밖을 고르지 않았는지 봅니다.
:::

:::caution[`because no identity-based policy allows`]
아직 권한을 주지 않았습니다. 서버에서 난 오류라면 그 서버의 IAM 역할에 필요한 정책을 붙입니다([9단원](/guestbook-lab/u9/)).
:::

:::caution[`Encoded authorization failure message` 만 보일 때]
이유가 암호처럼 감춰진 메시지입니다. 화면을 그대로 두고 손을 드세요. 강사가 메시지를 풀어 봅니다.
:::

:::caution[`403` `Forbidden` 만 보일 때]
같은 대상의 목록 보기(예: `aws s3 ls`)를 해 보면 이유가 적힌 메시지가 나옵니다.
:::

## http 주소가 안 열릴 때

서버, S3 웹사이트, 로드 밸런서 주소는 `http://` 입니다. 주소창에 IP 나 이름만 넣으면 Chrome 이 `https://` 로 바꿔 열다가 시간 초과가 납니다.

### 「사이트에 연결할 수 없음」이 뜹니다

:::caution[고칠 것]
> 「사이트에 연결할 수 없음」「응답하는 데 시간이 너무 오래 걸립니다」 `ERR_TIMED_OUT` `ERR_CONNECTION_TIMED_OUT`

브라우저가 주소를 https 로 바꿔 열었습니다. 우리 앱은 http 로만 열려 있습니다.

아래 순서로 고칩니다.

1. 그 탭은 닫습니다. 실패한 탭에서 고쳐 치면 계속 실패할 수 있습니다.
2. 새 탭에 `http://주소` 를 직접 입력합니다.
:::

### 「이 사이트는 보안 연결을 지원하지 않습니다」가 뜹니다

:::tip[정상입니다]{icon="approve-check-circle"}
「사이트로 이동」을 누르면 열립니다. 주소창의 「주의 요함」도 http 라서 뜨는 표시입니다.
:::
