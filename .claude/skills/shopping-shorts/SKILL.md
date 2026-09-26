---
name: shopping-shorts
description: Produce and upload affiliate shopping shorts (쇼핑 쇼츠) for YouTube Shorts, Instagram Reels and Threads — script, Higgsfield assets mixed with the owner's product photos, ffmpeg render with ad disclosure, private YouTube upload, and caption files for manual Instagram/Threads posting. Use when the user asks for 쇼핑 쇼츠, 쿠팡 파트너스/토스 쉐어링크 영상, or a product short.
---

# Shopping shorts pipeline

Work dir: `shopping-shorts/`. One folder per video: `jobs/<slug>/` (`job.json`, `assets/`, `out/`).
Links are the owner's job — never create, shorten or edit affiliate links. Videos point viewers to the profile link (Shorts description links are not clickable since 2023-08-31).
Stop at every **(confirm)** step.

## 1. Pick product
Read `products.csv` (owner fills it). Take rows without a `jobs/<slug>/out/final.mp4`.

## 2. Script → `jobs/<slug>/job.json`
Copy `jobs/sample-tumbler/job.json` as the schema. Rules:
- 10–30s, 3–6 scenes. Scene 1 = hook in ≤3s (problem or surprising benefit). Last scene = "구매 링크는 프로필에".
- Captions ≤ 28 Korean chars per scene. Only claims the owner gave in `key_points` — never invent specs, prices, discounts or reviews.
- `disclosure`: always set. Coupang → "광고 · 이 영상은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다". Toss → "광고 · 토스쇼핑 쉐어링크 활동으로 수수료를 받을 수 있습니다" (wording not yet checked against Toss policy — flag it).
- Put the same disclosure at the start of `youtube.description`, `caption_instagram`, `caption_threads`.
- Vary hook, order and visuals per video: YouTube's "inauthentic content" policy (renamed 2025-07-15) demonetizes mass-produced, near-identical videos.

## 3. Assets (confirm — Higgsfield costs credits)
Mix: owner photos/videos in `assets/` + Higgsfield clips.
- Ask before every generation; say model, count, resolution. Start with the cheapest option (Seedance 2.0 `mode: fast`, 720p, 5s, `generate_audio: false`) and report credits spent (`balance` before/after).
- Product-accurate shots: use the owner's product photo as `start_image`; do not generate fake product details or fake people giving testimonials.
- Save downloads into `jobs/<slug>/assets/` and reference them in `scenes[].media`.
- Optional voiceover via Higgsfield `generate_audio` → `assets/vo.mp3`. BGM only from sources the owner has rights to.

## 4. Render
`python scripts/render.py jobs/<slug>` (Windows uses 맑은 고딕 automatically; else `--font`).
Output: `out/final.mp4` (1080×1920, H.264/AAC), `out/instagram.txt`, `out/threads.txt`. Check a frame for text overflow.

## 5. Upload (confirm)
- YouTube: `python scripts/upload_youtube.py jobs/<slug>` → uploads **private** (unverified API projects are private-only anyway). Exit code 2 = token missing/expired → tell the owner to run `--login` themselves; never open a browser from automation.
- Tell the owner to check in YouTube Studio before switching to public: disclosure visible, "유료 프로모션 포함" setting, altered/synthetic content label.
- Instagram/Threads: owner posts `out/final.mp4` with `out/instagram.txt` / `out/threads.txt` manually.
- Google OAuth app in "Testing" status → token expires every 7 days; `last_login.txt` in the secrets folder holds the date — warn on day 6.

## 6. Log
Append one line per video to `shopping-shorts/log.csv`: date, slug, credits used, youtube url.
