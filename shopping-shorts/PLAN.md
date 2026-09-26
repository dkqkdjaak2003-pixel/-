# 쇼핑 쇼츠 프로젝트 계획 (2026-09-26)

## 구조
상품 선정 → 쇼츠 제작 → 유튜브·인스타·스레드 업로드
→ 인포크링크(프로필 링크) / 유튜브 쇼핑 태그(조건 충족 후)
→ 쿠팡 파트너스 · 토스 쉐어링크 → 구매 → 수수료

## 결정 사항
- 링크 허브: 인포크링크
- 유튜브 채널: 신규 개설 예정 → 초기엔 유튜브 쇼핑 태그 불가, 채널 프로필 링크 + 인포크링크로 유도
- 작업 환경: Windows 데스크톱 Claude Code

## 확인된 규칙 (출처 / 확인 수준)
| 항목 | 내용 | 확인 수준 |
|---|---|---|
| 쿠팡 파트너스 고지 | 대가성 문구 의무. 예: "이 게시물은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다." 위반 시 수익 몰수·자격 상실 가능 | 검색 요약. 공식 가이드 원문 대조 필요: https://partners.coupangcdn.com/partners-guide/partners-guide-20240716100922.pdf |
| 고지 위치 | 콘텐츠 첫 부분·제목 | 블로그 기준(https://onfmon.com/coupang-partners-fair-trade-commission-phrase/). 원문 대조 필요 |
| 토스 쉐어링크 | 클릭 후 24시간 내 결제 시 결제액 10%, 익월 25일 정산. "쉐어링크 공유" 버튼 링크만 인정 | 검색 요약. 원문 대조 필요: https://sharelink-docs.toss.im/help/policy |
| 유튜브 쇼핑 제휴 | 한국 지원, 쿠팡 연동. 음악·아동용 채널 불가 | 공식 고객센터(검색 요약): https://support.google.com/youtube/answer/13376398?hl=ko |
| 유튜브 쇼핑 구독자 기준 | 공식: YPP + 5,000명 초과 / 일부 블로그: 2026-03부터 500명 | ⚠️ 미확인. 공식 도움말 직접 확인 필요 |
| 쇼츠 설명·댓글 링크 | 2023-08-31부터 클릭 불가. 채널 프로필 링크는 클릭 가능 | Tubefilter 보도: https://www.tubefilter.com/2023/08/10/youtube-shorts-comments-spam/ |
| 공통 법규 | 공정위 「추천·보증 등에 관한 표시·광고 심사지침」: 경제적 이해관계 표시 | 법령 공개 자료 |

## 작업 계획
1. 규칙 확정: 쿠팡·토스·유튜브·인스타·스레드 공식 정책 원문 확인 → 채널별 고지 문구 템플릿
2. 상품 선정: 쿠팡·토스 모두 링크 발급 가능한 상품, 수수료·판매량 기준
3. 대본·소재: 15~30초 대본, Higgsfield Marketing Studio로 상품 영상 🛑 크레딧 사용
4. 편집: 9:16, 자막, 첫 화면 고지 문구 (ffmpeg)
5. 배포 점검: 인포크링크 링크·고지 문구 점검 후 업로드 🛑 외부 공개

## 데스크톱 이어받기 문구
```
주제: 쇼핑 쇼츠 제작. shopping-shorts/PLAN.md 먼저 읽고 이어서 진행.
1) 이 폴더 확인 후 쓸 도구 표로 추천 (Higgsfield Marketing Studio, ecc market-research, ffmpeg 등)
2) Higgsfield /mcp, 텔레그램, gh 연결 점검 보고
3) PLAN.md의 "미확인" 항목부터 공식 원문으로 확인
4) 먼저 물어볼 것: 첫 상품 카테고리, 채널 콘셉트, 주당 업로드 수
```

---

## 2차 결정 (2026-09-26)
- 역할: 링크 = 사장님 / 영상 제작·업로드 자동화 = Claude
- 유튜브: API로 **비공개** 업로드 → 사장님이 Studio에서 확인 후 공개
  (근거: 2020-07-28 이후 만든 미감사 API 프로젝트는 비공개로만 업로드됨 — https://developers.google.com/youtube/v3/docs/videos/insert)
- 인스타·스레드: 영상 파일 + 캡션 텍스트 자동 준비, 게시는 사장님 수동
  (근거: 두 API 모두 공개 URL로만 영상 게시 가능 — Meta 개발자 문서)
- 소재: Higgsfield 생성 + 사장님 실물 사진/영상 혼합
- Higgsfield 영상 1편 크레딧: API로 조회 불가(모델 정보에 가격 없음). 첫 생성 1건으로 실측 예정. 참고: 음성(Voiceover) 1건 0.15 크레딧(거래 내역 기준)

## 구성
| 파일 | 역할 |
|---|---|
| `.claude/skills/shopping-shorts/SKILL.md` | 전체 절차(대본→소재→렌더→업로드), 확인 관문 |
| `products.csv` | 사장님이 상품 입력 |
| `jobs/<slug>/job.json` | 영상 1편 설계(장면·자막·고지·캡션) |
| `scripts/render.py` | 9:16 편집, 자막, 전 구간 광고 고지, 음성·BGM 합성 |
| `scripts/upload_youtube.py` | 비공개 업로드. 토큰 없으면 브라우저 안 띄우고 종료(코드 2) |

## 데스크톱 1회 설정 (사장님)
1. ffmpeg 설치: `winget install Gyan.FFmpeg` (설치 후 새 터미널)
2. 파이썬 패키지: `uv pip install -r shopping-shorts/requirements.txt`
3. Google Cloud: 프로젝트 생성 → YouTube Data API v3 사용 설정 → OAuth 동의 화면(테스트, 본인 계정을 테스트 사용자로) → OAuth 클라이언트(데스크톱 앱) → JSON을 `%USERPROFILE%\.shopping-shorts-secrets\client_secret.json` 으로 저장
4. `python shopping-shorts/scripts/upload_youtube.py --login` → 브라우저에서 "허용"
   - 테스트 상태 앱은 7일마다 재로그인 필요

## 검증 기록 (클라우드 세션)
- render.py: 샘플(이미지 2 + 영상 1, 10초) → 1080×1920 H.264/AAC 10.0초 출력, 한글 자막·고지 정상 표시. 음성+BGM 합성도 10.0초 정상.
- upload_youtube.py: 토큰 없음 → 코드 2 종료 확인. 요청 본문은 공식 discovery 문서(revision 20260820) 필드와 일치(`containsSyntheticMedia`, `selfDeclaredMadeForKids`, `privacyStatus`). 실제 업로드는 미실행.
