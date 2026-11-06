// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// 학생 도움 페이지 「막혔을 때」. https://pghoya2956.github.io/guestbook-lab/ 로 공개한다.
// 빌드와 배포는 ../.github/workflows/pages.yml 이 main 에 push 할 때 한다.
// 덱 실습 장 꼬리말이 /u3 ~ /u15 주소를, 오리엔테이션 장과 2일차 표지 QR 이 첫 화면을 가리킨다. 슬러그를 바꾸면 덱도 고친다.
const units = (/** @type {number[]} */ ns) => ns.map((n) => `u${n}`);

export default defineConfig({
	site: 'https://pghoya2956.github.io',
	base: '/guestbook-lab',
	integrations: [
		starlight({
			title: '막혔을 때',
			description: 'AWS 클라우드 입문 실습 도움말. 화면에 보이는 문구로 내 단원 칸을 찾아 고칩니다.',
			defaultLocale: 'root',
			locales: { root: { label: '한국어', lang: 'ko' } },
			social: [{ icon: 'github', label: '공통 앱 저장소', href: 'https://github.com/pghoya2956/guestbook-lab' }],
			customCss: ['./src/styles/custom.css'],
			head: [
				// 예전 한 장짜리 페이지의 단원 주소(/#u7)로 들어오면 단원 페이지(/u7/)로 보낸다.
				{
					tag: 'script',
					content:
						"(()=>{const m=location.hash.match(/^#u(\\d+)$/);if(m&&/\\/guestbook-lab\\/?$/.test(location.pathname))location.replace('/guestbook-lab/u'+m[1]+'/')})()",
				},
			],
			sidebar: [
				{ label: '처음 오면', items: [{ label: '막혔을 때 순서', link: '/' }, 'basics/values', 'basics/errors', 'basics/ignore'] },
				{ label: '1일차', items: units([1, 3, 4, 5, 6, 7, 8]) },
				{ label: '2일차', items: units([9, 10, 11, 12, 13, 14, 15]) },
				{ label: '미니 프로젝트 메뉴', items: [{ autogenerate: { directory: 'menu' } }] },
			],
		}),
	],
});
