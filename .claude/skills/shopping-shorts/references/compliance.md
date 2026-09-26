# Compliance notes (checked 2026-09-26)

Re-check the sources when in doubt; rules and limits change.

## 1. 광고 표기 (Korea FTC 추천·보증 심사지침, 2024-12-01 시행 개정)
- Posts with any economic interest (cash, product, commission, points, discounts) must disclose it clearly.
- Text-centric media: disclosure in the title or at the beginning of the post.
- Conditional/uncertain wording like "수수료를 지급받을 수 있음" is listed as NOT a clear disclosure. Use definite wording.
- Sources: 공정위 보도자료 https://www.korea.kr/briefing/pressReleaseView.do?newsId=156660604 ,
  지침 원문 https://www.law.go.kr/LSW//admRulInfoP.do?admRulSeq=2100000249484&chrClsCd=010201 ,
  김·장 해설 https://www.kimchang.com/ko/insights/detail.kc?sch_section=4&idx=30702

Recommended text (Coupang Partners wording, definite form):
`이 게시물은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다.`
Put it on the first caption line AND on screen for the whole video (assemble.py does this). YouTube: must be visible without expanding "더보기".
- Sources: 쿠팡 파트너스 이용 가이드 https://partners.coupangcdn.com/partners-guide/partners-guide-20240716100922.pdf ,
  https://waneestudio.com/867/

## 2. Coupang Partners API
- API keys become available after final approval (reported condition: cumulative sales over 150,000 KRW).
- Search API reported limit: 10 calls/hour; repeated violations may restrict API use.
- Auth: HMAC-SHA256 `Authorization: CEA algorithm=HmacSHA256, access-key=…, signed-date=…, signature=…`.
- Sources: https://partners.coupang.com/ , https://uup.kr/blog/coupang-partners-api-key ,
  https://codedosa.com/12603 (secondary sources; confirm limits in the Partners portal API docs
  https://partner-developers.coupangcorp.com/hc/ko/categories/360005470572-API-Docs)

## 3. YouTube "inauthentic content" (renamed from "repetitious content", 2025-07-15)
- Mass-produced / template-like videos with little variation are not eligible for monetization. AI tools are allowed; each video needs meaningful variation and added value.
- Sources: https://support.google.com/youtube/answer/1311392 ,
  https://www.socialmediatoday.com/news/youtube-clarifies-monetization-update-inauthentic-repeated-content/752892/

## 4. Instagram API publishing
- Professional (Business/Creator) account required; Reels via `media_type=REELS`.
- Limit: 100 API-published posts per 24h moving window; check `GET /<IG_ID>/content_publishing_limit`.
- Flow: `POST /<IG_ID>/media` (media_type=REELS) → upload → poll container `status_code` until FINISHED → `POST /<IG_ID>/media_publish`.
- Resumable upload: container with `upload_type=resumable`, then POST the file to `https://rupload.facebook.com/ig-api-upload/<version>/<container-id>` with `offset` and `file_size` headers.
- Reels via API: MP4/MOV, up to 15 min and 300 MB (secondary source).
- Long-lived token: refresh with `GET https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token`; token must be ≥24h old and not expired; refreshed tokens last 60 days.
- Sources: https://developers.facebook.com/docs/instagram-platform/content-publishing/ ,
  https://developers.facebook.com/docs/instagram-platform/content-publishing/resumable-uploads/ ,
  https://developers.facebook.com/docs/instagram-platform/reference/refresh_access_token/ ,
  https://adaptlypost.com/blog/instagram-reels-api-max-length-file-size

## 5. YouTube Data API uploads
- Un-audited API projects created after 2020-07-28: every `videos.insert` upload is locked private until the project passes the compliance audit.
  Sources: https://developers.google.com/youtube/v3/docs/videos/insert , https://github.com/porjo/youtubeuploader/issues/86
- `status.containsSyntheticMedia` (added 2024-10-30) declares altered/synthetic content; `paidProductPlacementDetails.hasPaidProductPlacement` marks paid promotion.
  Sources: https://developers.google.com/youtube/v3/revision_history , https://developers.google.com/youtube/v3/docs/videos
- Square/vertical videos up to 3 min uploaded from 2024-10-15 are Shorts. Source: https://support.google.com/youtube/answer/15424877
- Links in Shorts descriptions/comments are not clickable since 2023-08-31; channel profile links are. Source: https://www.tubefilter.com/2023/08/10/youtube-shorts-comments-spam/
- OAuth consent screen in "Testing" (external users): refresh tokens expire after 7 days. Source: https://support.google.com/cloud/answer/15549945
- Upload quota changed in 2025-2026 (secondary sources report a separate upload bucket); check the Cloud console quota page and https://developers.google.com/youtube/v3/revision_history

## 6. Content honesty (표시광고법 기본 원칙)
- No fabricated reviews, ratings, rankings, discounts or usage results.
- No health/medical efficacy claims for foods, cosmetics, or devices without substantiation.
- Do not reuse other creators' videos or copy their scripts; use own footage, licensed assets, or generated footage.
