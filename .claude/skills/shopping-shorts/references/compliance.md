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
- Source: https://developers.facebook.com/docs/instagram-platform/content-publishing/

## 5. Content honesty (표시광고법 기본 원칙)
- No fabricated reviews, ratings, rankings, discounts or usage results.
- No health/medical efficacy claims for foods, cosmetics, or devices without substantiation.
- Do not reuse other creators' videos or copy their scripts; use own footage, licensed assets, or generated footage.
