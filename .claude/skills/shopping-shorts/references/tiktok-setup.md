# 틱톡 자동화 설정 (TikTok Content Posting API)

## 방식 선택
| 모드 | 권한(scope) | 동작 | 자동화 정도 |
| --- | --- | --- | --- |
| `draft` (기본) | `video.upload` | 영상을 틱톡 **초안함(인박스)** 으로 업로드 → 틱톡 앱 알림에서 캡션·음원 넣고 게시 | 업로드까지 자동, 게시는 탭 한 번 |
| `direct` | `video.publish` | 프로필에 바로 게시 | `approve` 명령(=게시 동의) 후에만 실행 |

틱톡 가이드라인은 게시물마다 사용자의 명시적 동의와 미리보기를 요구합니다. 그래서 오토파일럿은 `publish_mode: auto` 여도 `direct` 모드 틱톡은 승인 없이 올리지 않습니다.
draft 모드는 틱톡 앱에서 인기 음원을 붙일 수 있다는 장점도 있습니다.

## 설정
1. https://developers.tiktok.com 에서 앱 생성 → Login Kit + Content Posting API 추가 (Direct Post 쓰려면 활성화).
2. Redirect URI 등록: 링크 페이지 주소(예: `https://<아이디>.github.io/<저장소>/`) 사용 가능.
3. `autopilot/.env` 에 `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET` 입력.
4. 인증:
   ```
   S=.claude/skills/shopping-shorts/scripts
   python3 $S/tiktok_publish.py auth-url --redirect-uri https://<링크페이지>/
   # 브라우저에서 승인 → 이동된 주소창의 code=... 값을 복사
   python3 $S/tiktok_publish.py auth --redirect-uri https://<링크페이지>/ --code <복사한 값>
   python3 $S/tiktok_publish.py creator      # 계정·공개범위 옵션 확인
   ```
   access token 24시간, refresh token 365일 — 스크립트가 자동 갱신합니다.
5. **앱 검수(audit)** 신청: 검수 전에는 모든 게시물이 비공개(SELF_ONLY)로 제한되고 계정도 비공개여야 하며, 24시간 5명까지만 게시할 수 있습니다.

## 게시할 때 켜야 하는 것
- 콘텐츠 공개(Commercial content disclosure) → **브랜디드 콘텐츠** (쿠팡 파트너스 = 제3자 상품 홍보로 수수료 받음). direct 모드는 자동으로 `brand_content_toggle=true`.
- AI 생성 콘텐츠 라벨: Higgsfield 등으로 만든 사실적 영상이면 켜기 (direct 모드는 `is_aigc` 자동 설정).
- 캡션 첫 줄 광고 표기, 구매 링크는 프로필 링크 번호로 안내.

## 파일 제한
MP4/MOV/WebM, 영상 길이는 계정의 `max_video_post_duration_sec` 이하, 조각 업로드 5~64MB(마지막 조각 최대 128MB), 5MB 미만은 한 번에.
성과 수집(조회수)은 `video.list` 권한이 추가로 필요해 이번 버전에는 넣지 않았습니다.
