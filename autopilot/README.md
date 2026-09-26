# 쇼핑 쇼츠 오토파일럿

정해진 시간마다 **상품 소싱 → 대본 → 영상 생성 → 합성 → 자동 검수 → (승인) → 인스타 게시 → 링크 페이지 갱신 → 성과 수집 → 다음 기획에 반영** 을 반복합니다.

```
cron ─▶ autopilot.py run
          ├─ source    쿠팡 파트너스 API(골드박스/베스트/검색) → 필터(가격·로켓·제외 카테고리·중복)
          │            → Claude가 1개 선택 → subId 달린 딥링크 + 링크 번호 부여
          ├─ script    Claude: script.json / caption.txt(첫 줄 광고표기) / shotlist.md
          ├─ footage   higgsfield 모드: Claude + Higgsfield MCP 로 장면 영상·음성 생성
          │            inbox 모드: 알림 → 직접 촬영해 폴더에 넣으면 다음 실행에 이어감
          ├─ assemble  ffmpeg 1080×1920, 자막 + 광고표기 상시 노출
          ├─ qa        해상도·길이·광고표기·금지표현·캡션 URL 검사 (실패 시 중단+알림)
          └─ publish   review 모드: 알림 → approve 명령 / auto 모드: 즉시 게시 (일일 상한)
                       인스타 릴스 + 유튜브 쇼츠 + 틱톡 (플랫폼별로 성공 기록 → 한쪽 실패 시 그쪽만 다음 실행에 재시도)
                       틱톡: draft 모드 = 초안함 업로드 후 앱에서 탭 한 번 게시 / direct 모드 = approve 후에만 게시
                       → shorts/links.json → docs/index.html (프로필 링크용 번호 검색 페이지)
cron ─▶ autopilot.py report
          인스타 인사이트 + 유튜브 조회수/좋아요 + 쿠팡 커미션 리포트 → shorts/learnings.md → 다음 source/script 프롬프트에 주입
```

각 작업은 `shorts/<작업ID>/job.json` 에 단계가 저장되어, 중간에 끊겨도 다음 실행에서 이어집니다.

## 설치 (PC 1회)
1. Python 3.9+, ffmpeg(libass 포함), 한글 폰트, Git
2. Claude Code CLI 설치 후 로그인. Higgsfield MCP 연결:
   `claude mcp add --transport http higgsfield https://mcp.higgsfield.ai/mcp` → `claude` 실행 후 `/mcp` 에서 로그인
3. `cp autopilot/.env.example autopilot/.env` 후 키 입력 (쿠팡 파트너스 API 키, 인스타 토큰 — `.claude/skills/shopping-shorts/references/instagram-setup.md`)
   유튜브: `references/youtube-setup.md` 순서대로 OAuth 인증 1회 + **API 검수 신청** (검수 전 업로드는 비공개로 잠김).
   틱톡: `references/tiktok-setup.md` (앱 생성·인증·검수 신청).
   안 쓰는 플랫폼은 `config.json` 의 `"platforms"` 에서 빼세요.
4. `cp autopilot/config.example.json autopilot/config.json` 후 니치·키워드·가격대 수정
5. 1회 수동 실행: `autopilot/run_daily.sh run` → `python3 autopilot/autopilot.py status`
6. 예약 실행 — macOS/Linux `crontab -e`:
   ```
   7 10,19 * * * /경로/autopilot/run_daily.sh run
   37 23 * * *   /경로/autopilot/run_daily.sh report
   ```
   Windows: 작업 스케줄러에서 `python autopilot\autopilot.py run` (시작 위치 = 저장소 폴더), 환경변수는 시스템 환경변수로 등록.
   PC가 켜져 있어야 실행됩니다.

## 링크 페이지 (프로필 링크)
인스타 캡션과 유튜브 쇼츠 설명의 URL은 클릭되지 않으므로, 영상 끝에 "프로필 링크 N번"을 안내하고 `docs/index.html` 에서 번호로 찾게 합니다.
GitHub 저장소 Settings → Pages → Branch 의 `/docs` 폴더로 배포하고, 그 주소를 인스타 프로필 링크와 유튜브 채널 링크(채널 맞춤설정 → 기본 정보 → 링크)에 넣으세요.
`config.json` 의 `linkpage.git_push: true` 로 두면 게시할 때마다 자동 커밋·푸시합니다.

## 운영 모드 권장
- 처음 2주: `"publish_mode": "review"` — 알림 받고 `final.mp4` 확인 후 `approve <ID>` / `reject <ID> 사유`
- 품질이 안정되면 `"auto"` 로 전환. 자동 검수(QA)와 일일 상한(`max_posts_per_day`)은 계속 적용됩니다.
- 알림: `notify_cmd` 에 셸 명령을 넣으면 `$MESSAGE` 로 전달됩니다. 예) ntfy.sh 앱:
  `"notify_cmd": "curl -s -d \"$MESSAGE\" https://ntfy.sh/<내 토픽>"`

## 비용·한도
- Claude Code 사용량(구독 또는 API), Higgsfield 크레딧(영상 1개당 장면 수만큼 생성).
- 쿠팡 검색 API는 시간당 약 10회 → 실행 1회당 검색 1회만 호출, 6시간 캐시.
- 인스타 API 게시 24시간 100개 한도. 실제로는 하루 1~3개가 적당합니다.
- 유튜브 업로드 할당량은 2025~2026년에 바뀌었습니다. Cloud 콘솔 할당량 페이지에서 확인하세요.

## 한계 (자동화할 수 없는 것)
- 쿠팡 파트너스 최종 승인(누적 판매 조건), 인스타/Meta 앱 설정·토큰 발급은 직접 해야 합니다.
- 인기 음원 삽입, 댓글 키워드 DM 자동응답은 이 구조에 포함되지 않습니다(DM 자동화는 웹훅 서버 필요).
- 쿠팡 리포트 API 경로는 공개 SDK 기준이라, 404가 나면 파트너스 포털 문서로 경로를 확인해야 합니다.
