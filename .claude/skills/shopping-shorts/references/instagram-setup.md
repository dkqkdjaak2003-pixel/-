# Instagram 자동 게시 설정 (Instagram API with Instagram Login)

Meta 화면 이름은 자주 바뀝니다. 막히면 https://developers.facebook.com/docs/instagram-platform/overview/ 를 기준으로 확인하세요.

1. 인스타그램 계정을 **프로페셔널 계정**(비즈니스 또는 크리에이터)으로 전환 (인스타 앱 → 설정 → 계정 유형).
2. https://developers.facebook.com/apps 에서 앱 생성 → 인스타그램 사용 사례/제품 추가 → "API setup with Instagram login".
3. 본인 인스타 계정을 앱에 연결(역할/테스터 추가 후 인스타 앱에서 초대 수락)하고 대시보드에서 액세스 토큰 생성.
   권한: `instagram_business_basic`, `instagram_business_content_publish`.
   다른 사람 계정에 게시하려면 앱 검수(App Review)가 필요합니다. 본인 계정 운영 용도면 보통 필요 없지만 대시보드 안내를 따르세요.
4. 환경변수 설정 (토큰은 저장소에 커밋하지 말 것):
   ```
   export IG_ACCESS_TOKEN=...   # 장기 토큰
   python3 .claude/skills/shopping-shorts/scripts/instagram_publish.py me   # user_id 확인
   export IG_USER_ID=...
   ```
5. 확인: `instagram_publish.py limit` 가 quota_usage 를 돌려주면 준비 완료.
6. 토큰 유지: 60일마다 만료 → 한 달에 한 번 `instagram_publish.py refresh` 실행 후 새 토큰으로 교체.

## 알려진 제약
- 24시간 동안 API 게시 100개 (content_publishing_limit 로 확인).
- 캡션 속 URL은 클릭되지 않음 → 구매 링크는 프로필 링크 또는 DM 안내.
- 인기 음원(트렌딩 오디오)은 API로 붙일 수 없음 → 필요한 영상은 앱에서 수동 업로드.
