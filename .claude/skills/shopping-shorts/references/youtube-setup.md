# 유튜브 자동 업로드 설정 (YouTube Data API v3)

1. https://console.cloud.google.com 에서 프로젝트 생성 → "YouTube Data API v3" 사용 설정.
2. OAuth 동의 화면(Google Auth Platform): 사용자 유형 "외부", 본인 계정을 테스트 사용자로 추가 →
   준비되면 게시 상태를 **"프로덕션(In production)"** 으로 변경.
   "테스트" 상태에서는 refresh token 이 7일 뒤 만료되어 예약 업로드가 멈춥니다.
3. 사용자 인증 정보 → OAuth 클라이언트 ID → 유형 "데스크톱 앱" → JSON 다운로드 (`client_secret.json`, git에 올리지 말 것).
4. 인증 (브라우저가 열림, 업로드할 채널 계정으로 로그인):
   ```
   python3 .claude/skills/shopping-shorts/scripts/youtube_publish.py auth --client-secret client_secret.json
   ```
   토큰은 `~/.config/shopping-shorts/youtube_token.json` 에 저장됩니다 (`YT_TOKEN_FILE` 로 변경 가능).
5. **API 검수(audit) 신청 — 공개 업로드에 필수.** 2020-07-28 이후 만든 검수 전 프로젝트로 올린 영상은 모두 비공개로 잠깁니다.
   YouTube API Services 감사 신청서(개발자 문서의 "Audit and Quota Extension Form")를 제출하세요. 승인 전까지는 업로드해도 비공개로 남습니다.
6. 테스트: `youtube_publish.py upload final.mp4 --meta youtube.json --privacy private --dry-run`

## 알아둘 점
- 세로/정사각형 3분 이하 영상은 자동으로 쇼츠로 분류됩니다 (2024-10-15 이후 업로드).
- 쇼츠 설명·댓글의 링크는 클릭되지 않습니다 (2023-08-31부터). 채널 프로필 링크에 링크 페이지를 넣고 번호로 안내하세요.
- 업로드 시 `paidProductPlacementDetails.hasPaidProductPlacement=true`(유료 프로모션 표시)와 `containsSyntheticMedia`(AI 생성 사실적 콘텐츠)를 설정합니다. API가 유료 프로모션 필드를 거부하면 그 필드 없이 다시 올리고 경고를 남기니, 그때는 YouTube 스튜디오에서 직접 체크하세요.
- 할당량: 업로드 비용·한도는 최근 여러 번 바뀌었습니다. Google Cloud 콘솔의 할당량 페이지와 공식 revision history 를 확인하세요.
