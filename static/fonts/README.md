# 글꼴

화면 글꼴은 외부에서 부르지 않고 이 폴더의 파일을 서버가 직접 준다. 둘 다 SIL Open Font License 1.1 이다.

| 파일 | 원본 | 라이선스 |
|---|---|---|
| `noto-sans-kr-400.woff2`, `-700`, `-900` | Noto Sans KR 가변 글꼴(google/fonts `ofl/notosanskr`)에서 굵기 400, 700, 900 을 뽑음 | `OFL-NotoSansKR.txt` |
| `roboto-mono-400.woff2` | Roboto Mono 가변 글꼴(google/fonts `ofl/robotomono`)에서 굵기 400 을 뽑음 | `OFL-RobotoMono.txt` |

한글 글꼴은 크기를 줄이려고 KS X 1001 완성형 한글 2350자, 한글 자모, 기본 라틴 문자, 문장 부호만 남겼다. 이 밖의 글자(예: 똠, 햏)는 브라우저가 기기 글꼴로 대신 그린다.

다시 만들 때는 fontTools 로 굵기를 고정한 뒤(`varLib.instancer`) 같은 글자 범위로 줄여 woff2 로 저장한다.
