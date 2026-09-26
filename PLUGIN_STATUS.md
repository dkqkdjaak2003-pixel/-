# Claude Code 플러그인 설치 현황 (2026-09-25)

- Claude Code 버전: 2.1.282

## 플러그인 (user scope, `claude plugin list` 기준 모두 enabled)

| 플러그인 | 버전 | 스킬 수 | 출처 |
| --- | --- | --- | --- |
| finance@knowledge-work-plugins | 1.3.0 | 8 | anthropics/knowledge-work-plugins |
| legal@knowledge-work-plugins | 1.3.0 | 9 | anthropics/knowledge-work-plugins |
| marketing-skills@marketingskills | 2.11.1 | 50 | coreyhaines31/marketingskills |
| social-media-skills@social-media-skills | 1.1.0 | 17 | charlie947/social-media-skills |

## 디자인 스킬 (npx skills, 프로젝트 `.claude/skills/`)

- nextlevelbuilder/ui-ux-pro-max-skill: banner-design, brand, design, design-system, slides, ui-styling, ui-ux-pro-max
- Leonxlnx/taste-skill: design-taste-frontend

## 재현

`.claude/settings.json`에 `extraKnownMarketplaces`와 `enabledPlugins`가 들어 있어, 이 저장소에서 Claude Code를 열면 같은 플러그인을 설치하라는 안내가 나옵니다.

## 동화 영상 자동화 (2차 작업)

- 프로젝트 스킬 `.claude/skills/kids-story-video/` 추가: 기획 → 스토리 → 장면 대본 → 프롬프트 → Higgsfield 생성 → 편집 → 업로드 체크리스트
- 마켓플레이스 등록만 됨 (플러그인 설치는 권한 문제로 보류): `higgsfield` (higgsfield-ai/skills), `caveman` (JuliusBrussee/caveman)
- 사용자가 직접 실행해야 함:
  - `claude plugin install higgsfield@higgsfield`
  - `claude plugin install caveman@caveman`
  - `claude mcp add --transport http higgsfield https://mcp.higgsfield.ai/mcp` 후 `/mcp`에서 브라우저 로그인

## 쇼핑 쇼츠 자동화 (3차 작업)

- 프로젝트 스킬 `.claude/skills/shopping-shorts/` 추가: 기획 → 쿠팡 파트너스 상품 소싱 → 대본 → 촬영/AI 영상(Higgsfield) → 음성 → ffmpeg 합성(광고 표기 자동 삽입) → 업로드 체크리스트
- `scripts/coupang_partners.py`: 쿠팡 파트너스 API(검색·골드박스·카테고리 베스트·딥링크), 표준 라이브러리만 사용, 검색 결과 6시간 캐시
- `scripts/assemble.py`: 장면 클립 → 1080×1920 합성, 자막·광고 표기 문구 번인 (ffmpeg + libass + 한글 폰트 필요)
- `references/compliance.md`: 공정위 추천·보증 지침, 쿠팡 파트너스 표기, YouTube 정책, Instagram API 제한 출처
- 사용자가 준비할 것: 쿠팡 파트너스 최종 승인 후 API 키(`COUPANG_ACCESS_KEY`, `COUPANG_SECRET_KEY` 환경변수), ffmpeg 설치
