---
title: "메뉴 1. 급식 사진 첨부"
sidebar:
  label: "1. 급식 사진 첨부"
  order: 1
---

쓰는 서비스: S3, IAM 역할

완료 기준: 메뉴를 골라 올린 급식 사진이 리뷰와 식판의 그 칸에 보인다

## 바뀌는 구조

급식 리뷰 앱 서버가 사진을 S3 버킷의 `images/` 아래에 저장하고, 페이지에는 잠깐만 유효한 주소(미리 서명된 URL)로 보여 줍니다. 미리 서명된 URL 은 잠깐만 열리는 사진 주소입니다. 서버가 자기 역할의 권한으로 서명해 만들고 1시간이 지나면 열리지 않습니다. 버킷은 공개하지 않습니다.

## 만들 것

1. 사진을 담을 버킷을 만듭니다. <a href="https://s3.console.aws.amazon.com/s3/bucket/create?region=ap-northeast-2" target="_blank" rel="noopener">콘솔 열기 ↗</a>
   1. 「버킷 이름」 칸에 `guestbook-img-[좌석 번호]-[숫자]` 를 넣습니다. 예: `guestbook-img-s01-1112`

      ![버킷 만들기 화면의 버킷 이름 칸에 guestbook-img 로 시작하는 이름을 넣은 화면](../../../assets/menu1/img-bucket-create.png)

   2. 아래로 내려 「모든 퍼블릭 액세스 차단」이 켜져 있는지 봅니다. 켜진 그대로 두고 맨 아래 「버킷 만들기」를 누릅니다.

      ![모든 퍼블릭 액세스 차단 체크가 켜져 있는 화면](../../../assets/menu1/img-bucket-block.png)

2. 서버 역할에 이 버킷에 사진을 넣고 읽을 권한을 붙입니다. <a href="https://console.aws.amazon.com/iam/home#/roles/details/guestbook-ec2-role?section=permissions" target="_blank" rel="noopener">guestbook-ec2-role 열기 ↗</a>
   1. IAM 역할 목록에서 `guestbook-ec2-role` 을 엽니다. 「권한 정책」 표 오른쪽 위 「권한 추가」(①) → 「인라인 정책 생성」(②)을 누릅니다. 인라인 정책은 이 역할에만 붙는 권한 쪽지입니다.

      ![guestbook-ec2-role 의 권한 추가 단추와 펼친 메뉴의 인라인 정책 생성에 번호를 붙여 표시한 화면](../../../assets/menu1/role-inline-menu.png)

   2. 「정책 편집기」 오른쪽 「JSON」(①)을 누릅니다. JSON 은 권한을 적는 정해진 글 형식입니다. 아래 `Resource` 줄의 `arn:aws:s3:::…` 는 ARN, 즉 AWS 자원의 전체 주소입니다. 편집기 칸(②)의 내용을 모두 지우고 아래를 붙여 넣습니다. `버킷이름` 자리에는 1번에서 만든 버킷 이름을 넣습니다.

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

      ![정책 편집기의 JSON 단추와 정책을 붙여 넣은 편집기 칸에 번호를 붙여 표시한 화면](../../../assets/menu1/policy-json.png)

   3. 맨 아래 「다음」을 누릅니다. 「정책 이름」에 `guestbook-image` 를 넣습니다.

      ![검토 및 생성 단계의 정책 이름 칸에 guestbook-image 를 넣은 화면](../../../assets/menu1/policy-name.png)

   4. 맨 아래 「정책 생성」을 누릅니다.

      ![검토 및 생성 단계 맨 아래 정책 생성 단추에 표시한 화면](../../../assets/menu1/policy-create.png)

3. 로드 밸런서 뒤 서버 두 대를 찾습니다. 오토 스케일링이 만든 서버는 「Name」 칸이 비어 있어서 대상 그룹에서 인스턴스 ID 로 찾습니다. <a href="https://ap-northeast-2.console.aws.amazon.com/ec2/home?region=ap-northeast-2#TargetGroups:" target="_blank" rel="noopener">대상 그룹 ↗</a>
   1. 대상 그룹 목록에서 `guestbook-tg` 이름을 누릅니다.

      ![대상 그룹 목록에서 guestbook-tg 이름 링크에 표시한 화면](../../../assets/menu/find-tg.png)

   2. 아래 「대상」 탭(①)에 인스턴스 ID 두 개(②)가 보입니다. 두 ID 의 끝 네 글자를 적어 둡니다.

      ![guestbook-tg 의 대상 탭과 등록된 인스턴스 ID 두 개에 번호를 붙여 표시한 화면](../../../assets/menu/find-targets.png)

   3. 인스턴스 목록에서 첫 번째 ID 의 행을 체크(①)합니다. 「인스턴스 ID」(②)가 적어 둔 것과 같은지 보고 「연결」(③)을 누릅니다. 연결 화면에서 「SSM Session Manager」 카드 → 「연결」은 [9단원](/guestbook-lab/u9/) 4번과 같습니다. <a href="https://ap-northeast-2.console.aws.amazon.com/ec2/home?region=ap-northeast-2#Instances:" target="_blank" rel="noopener">인스턴스 ↗</a>

      ![인스턴스 목록에서 이름이 빈 서버 행 체크, 인스턴스 ID, 연결 단추에 번호를 붙여 표시한 화면](../../../assets/menu/find-instance.png)

4. 첫 번째 서버에서 설정 파일을 고칩니다. 설정 파일에는 메뉴마다 쓸 줄이 미리 비어 있습니다. 새 줄을 더하면 같은 이름이 두 줄이 되고 아래쪽 줄 값이 쓰여서 헷갈리니 이미 있는 줄에 이어 씁니다.
   1. 설정 파일을 엽니다. 빈 `IMAGE_BUCKET=` 줄이 보입니다.

      ```bash
      # 앱 설정 파일을 nano 편집기로 엽니다
      sudo nano /opt/guestbook/config.env
      ```

      ![nano 로 연 config.env 에서 빈 IMAGE_BUCKET= 줄에 표시한 화면](../../../assets/menu1/nano-before.png)

   2. 화살표 키로 `IMAGE_BUCKET=` 줄 끝까지 가서 `=` 바로 뒤에 버킷 이름을 적습니다(①). Ctrl+O(②)를 누르고 Enter 로 저장한 뒤 Ctrl+X(③)로 나옵니다.

      ```text
      IMAGE_BUCKET=버킷이름
      ```

      ![IMAGE_BUCKET= 뒤에 버킷 이름을 적은 줄과 아래쪽 ^O Write Out, ^X Exit 에 번호를 붙여 표시한 화면](../../../assets/menu1/nano-after.png)

   3. 적은 줄을 다시 확인합니다.

      ```bash
      # 설정 파일 내용을 화면에 출력해 고친 줄을 확인합니다
      cat /opt/guestbook/config.env
      ```

      ![cat 으로 출력한 설정 파일에서 IMAGE_BUCKET= 뒤에 버킷 이름이 붙은 줄에 표시한 화면](../../../assets/menu1/cat-check.png)

   4. 앱을 다시 켭니다.

      ```bash
      # 앱을 다시 켜서 바뀐 설정을 읽게 합니다
      sudo systemctl restart guestbook
      ```

5. 두 번째 서버에서도 똑같이 합니다. 3번의 3단계에서 두 번째 ID 의 행만 체크해 연결하고 4번을 그대로 합니다. 한 대만 바꾸면 새로고침할 때마다 「급식 사진」 단추가 보였다 안 보였다 합니다.

## 확인

1. 새 탭에 `http://로드 밸런서 DNS 이름` 을 엽니다([12단원](/guestbook-lab/u12/) 5번). 「리뷰 남기기」에 「급식 사진」 단추가 생깁니다. 「어떤 메뉴」(①)에서 사진의 음식을 고르고, 「급식 사진」(②)으로 사진을 고른 뒤 한줄평을 쓰고 「리뷰 올리기」(③)를 누릅니다. 휴대폰에서 누르면 바로 찍거나 사진첩에서 고를 수 있습니다. <a href="https://ap-northeast-2.console.aws.amazon.com/ec2/home?region=ap-northeast-2#LoadBalancers:" target="_blank" rel="noopener">로드 밸런서 ↗</a>

   ![리뷰 남기기의 어떤 메뉴 칸, 고른 사진 이름이 보이는 급식 사진 단추, 리뷰 올리기 단추에 번호를 붙여 표시한 화면](../../../assets/menu1/app-form.png)

   진짜 급식 사진이 없으면 아래 견본 사진을 내려받아 올립니다. 이름을 누르면 내 컴퓨터의 「다운로드」 폴더에 저장되고, 「급식 사진」을 누른 창에서 그 폴더를 열어 고릅니다. 모두 재사용이 허락된 사진입니다([출처](https://github.com/pghoya2956/guestbook-lab/blob/main/site/public/samples/CREDITS.md)).

   <a href="/guestbook-lab/samples/hyeonmi-bap.jpg" download>현미밥</a>, <a href="/guestbook-lab/samples/sogogi-miyeokguk.jpg" download>소고기미역국</a>, <a href="/guestbook-lab/samples/dakgalbi.jpg" download>닭갈비</a>, <a href="/guestbook-lab/samples/kongnamul-muchim.jpg" download>콩나물무침</a>, <a href="/guestbook-lab/samples/baechu-kimchi.jpg" download>배추김치</a>, <a href="/guestbook-lab/samples/gyul.jpg" download>귤</a>

2. 고른 메뉴의 식판 칸(①)이 올린 사진으로 바뀌고, 리뷰 위 사진 줄(②)과 리뷰 오른쪽에도 사진이 보입니다. 칸 사진은 그 메뉴로 올라온 가장 최근 사진입니다. 메뉴를 고르지 않은 사진은 리뷰에만 보입니다.

   ![닭갈비 식판 칸이 올린 사진으로 채워지고 아래 사진 줄에 같은 사진이 보이는 화면에 번호를 붙여 표시한 화면](../../../assets/menu1/app-image.png)

3. 사진 버킷의 「객체」 탭에 `images/` 폴더가 생겼는지 봅니다. <a href="https://s3.console.aws.amazon.com/s3/buckets?region=ap-northeast-2" target="_blank" rel="noopener">버킷 목록 ↗</a>

   ![사진 버킷의 객체 탭에 생긴 images/ 폴더에 표시한 화면](../../../assets/menu1/s3-images.png)

## 막히면

- 새로고침하면 사진 붙은 리뷰와 식판 칸 사진이 보였다 안 보였다 합니다: 리뷰는 아직 서버마다 자기 디스크에 저장됩니다(`저장소: file`). 사진은 S3 에 있지만 리뷰는 올린 서버에만 남습니다. [메뉴 2](/guestbook-lab/menu/2-dynamodb/)까지 하면 두 서버가 같은 리뷰와 사진을 보여 줍니다.
- 사진을 올렸는데 식판 칸이 그대로입니다: 「어떤 메뉴」를 고르지 않고 올렸습니다. 메뉴를 고르고 한 번 더 올립니다.
- 새로고침마다 「급식 사진」 단추가 보였다 사라집니다: 4번을 한 서버에만 했습니다. 두 번째 서버도 고칩니다.
- 올리면 「리뷰를 저장하지 못했습니다」가 나옵니다: 사진을 버킷에 올릴 권한이 없습니다. 정책의 버킷 이름과 `images/*` 경로를 봅니다. 서버에서 `sudo journalctl -u guestbook -n 30` 끝부분에 `AccessDenied` 가 보입니다.
- `IMAGE_BUCKET=` 줄을 못 찾겠습니다: nano 에서 Ctrl+W 를 누르고 `IMAGE_BUCKET` 을 쳐서 Enter 를 누르면 그 줄로 갑니다.
- 오토 스케일링이 서버를 새로 만들면(교체, 늘리기) 새 서버의 설정 파일은 처음 상태입니다. 새 서버도 3번과 4번 순서로 고칩니다.
