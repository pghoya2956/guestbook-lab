# guestbook-lab 작업 지침

학생이 clone 하고 fork 하는 **공개 저장소**다. 강사용 계정 구성·관측·정리 코드는 여기에 두지 않는다(상위 폴더 `aws-lab/`, 비공개).

- 시크릿, AWS 계정 ID, 학생 이름·이메일, 학교 내부 정보를 커밋하지 않는다. 예시 값은 `버킷이름`, `계정ID` 처럼 자리 표시로 쓴다.
- 앱은 80 포트로 뜬다(학교망은 비표준 포트를 막을 수 있다). 서버 접속은 Session Manager 기준이라 SSH 관련 파일을 두지 않는다.
- 수업 덱의 단원 번호와 이 저장소의 파일·주소가 맞물려 있다. 경로·주소·설정 이름을 바꾸면 덱과 `site/src/content/docs/`(단원 페이지, 메뉴 안내)를 같이 고친다.
- `site/` 는 학생 실습 런북이다(Astro Starlight, 단원마다 「따라 하기」와 「막혔을 때」). main 에 push 하면 `.github/workflows/pages.yml` 이 빌드해 https://pghoya2956.github.io/guestbook-lab/ 로 낸다(Pages 원본은 GitHub Actions). 단원 페이지 주소 `/u1/`, `/u3/`~`/u15/` 를 덱 실습 장 꼬리말이, 첫 화면을 덱 QR 이 가리키니 슬러그를 바꾸면 덱도 고친다. 상자는 「고칠 것」이 `:::caution[고칠 것]`, 「정상입니다」가 `:::tip[정상입니다]{icon="approve-check-circle"}` 다. 로컬 확인은 `cd site && npm ci && npm run build`(Node 22.23.4 이상) 뒤 `npx astro preview`.
- 학생이 읽는 문서는 한국어로, 오류가 났을 때 무엇을 볼지까지 적는다.
- 테스트: `uv run --no-project --python 3.11 --with 'flask>=3.0,<4' --with boto3 --with pymysql --with 'moto[ssm,dynamodb,s3]' --with pytest python -m pytest -q` (MySQL 테스트는 docker 가 있으면 mysql:8.4 컨테이너로 돈다)
