# guestbook-lab 작업 지침

학생이 clone 하고 fork 하는 **공개 저장소**다. 강사용 계정 구성·관측·정리 코드는 여기에 두지 않는다(상위 폴더 `aws-lab/`, 비공개).

- 시크릿, AWS 계정 ID, 학생 이름·이메일, 학교 내부 정보를 커밋하지 않는다. 예시 값은 `버킷이름`, `계정ID` 처럼 자리 표시로 쓴다.
- 앱은 80 포트로 뜬다(학교망은 비표준 포트를 막을 수 있다). 서버 접속은 Session Manager 기준이라 SSH 관련 파일을 두지 않는다.
- 수업 덱의 단원 번호와 이 저장소의 파일·주소가 맞물려 있다. 경로·주소·설정 이름을 바꾸면 덱과 `docs/menu/` 를 같이 고친다.
- 학생이 읽는 문서는 한국어로, 오류가 났을 때 무엇을 볼지까지 적는다.
- 테스트: `uv run --no-project --python 3.11 --with 'flask>=3.0,<4' --with boto3 --with pymysql --with 'moto[ssm,dynamodb]' --with pytest python -m pytest -q` (MySQL 테스트는 docker 가 있으면 mysql:8.4 컨테이너로 돈다)
