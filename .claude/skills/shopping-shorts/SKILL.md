---
name: shopping-shorts
description: Source affiliate products (Coupang Partners) and produce vertical shopping shorts (Instagram Reels / YouTube Shorts / TikTok) end to end — product sourcing, hook script, AI or own footage, voice, ffmpeg assembly with ad disclosure, and publish checklist. Use when the user asks for 쇼핑 쇼츠, 제품 추천 릴스, 쿠팡 파트너스 영상, affiliate product shorts, or product sourcing for shorts.
---

# Shopping shorts pipeline

Work in stages. Save each stage to `shorts/<yyyymmdd>-<slug>/` so later stages read files instead of regenerating context. Stop at every **(confirm)** stage and wait for the user. Never invent product facts (price, specs, reviews, ratings, "1위", discounts) — only use what the API response or the product page states, and record the date you read it.

Compliance rules with sources are in `references/compliance.md`. Read it before stage 3 and stage 7.

## 1. Brief (confirm)
Ask only for what is missing and write `brief.md`:
- Niche (주방/자취템/차량/반려동물/육아…), target viewer, platforms
- Affiliate program (default: Coupang Partners) and whether API keys exist
- Footage mode: **A. own footage** (user films the product; most original) / **B. AI footage** from product images (Higgsfield) / **C. mix**
- Voice: user's voice, AI voice, or captions only
- Videos per week (keep it realistic; see "inauthentic content" in compliance)

## 2. Sourcing (confirm)
With `COUPANG_ACCESS_KEY` / `COUPANG_SECRET_KEY` set:
```
python3 .claude/skills/shopping-shorts/scripts/coupang_partners.py goldbox
python3 .claude/skills/shopping-shorts/scripts/coupang_partners.py best <categoryId> --limit 20
python3 .claude/skills/shopping-shorts/scripts/coupang_partners.py search "<keyword>" --limit 10
```
- Search is limited (reported ~10 calls/hour, repeated overuse can suspend API access). Plan keywords first, one call per keyword; results are cached 6h.
- Without keys (API is unlocked only after Partners final approval), ask the user to paste product URLs, or pick from their own list. Do not scrape Coupang pages.
- Score candidates in `candidates.md` (table): name, price as returned, rocket delivery, category, **visual demo-ability** (can the benefit be shown in 3s?), problem it solves, price band fit, season fit, risk (health/cosmetic/food claims → skip unless user insists and claims are supported).
- Present top 5; user picks. Save the chosen raw API JSON to `product.json`.
- Create the tracking link: `coupang_partners.py deeplink <productUrl>` → store `shortenUrl` in `product.json`.

## 3. Script (confirm)
`script.md` + `script.json` (format in `scripts/assemble.py` docstring). 15–30s, 5–8 scenes:
1. Hook ≤2s: problem or surprising result on screen (use `social-media-skills:hook-generator` if installed). Write 3 hook options, user picks.
2. Problem (relatable)
3. Demo — the product solving it (the core; 40–50% of runtime)
4. 1–2 factual details (only from `product.json` / product page)
5. CTA: "프로필 링크" / "댓글에 'OO' 남기면 DM" (Instagram captions do not have clickable links)
Rules: no fake before/after, no fake "써봤는데" testimonial when nobody used it, no efficacy claims for health/beauty/food. First caption line and `script.json.disclosure` carry the ad disclosure.

## 4. Footage (confirm — B/C cost Higgsfield credits)
- **A. own footage**: write `shotlist.md` (per scene: angle, action, 3–5s, 9:16, hands-only is fine). User films; files go to `assets/`.
- **B. AI footage** via Higgsfield MCP: upload the product image (`media_upload` / `media_import_url`), then product-shot / UGC presets (`get_presets source:'marketing_studio'`, `show_marketing_studio_v2`) or `generate_image` → image-to-video `generate_video`. Keep the product's real look (shape, color, logo) — do not alter it in ways that misrepresent the item. For multiple scenes call `get_workflow_instructions` first; batch generations and `jobs_wait`.
- Save clips as `assets/s<n>.mp4`. If Higgsfield is not connected, stop and say so; never fake outputs.

## 5. Voice & music
- AI voice: Higgsfield `generate_audio` (list voices with `list_voices`), save `assets/voice.mp3`.
- Music: only tracks the user has rights to, or add trending audio inside the platform app at upload time (licensed there). Set paths in `script.json`.

## 6. Assemble
```
python3 .claude/skills/shopping-shorts/scripts/assemble.py shorts/<dir>
```
Needs ffmpeg with libass and a Korean font (set `"font"` in `script.json`, e.g. "Noto Sans KR", "Apple SD Gothic Neo", "Malgun Gothic"). Output: `final.mp4` 1080×1920/30fps, captions + disclosure burned in. Check one frame visually before publishing. Without ffmpeg, write an edit list for CapCut instead.

## 7. Publish (confirm — posting is public)
Write `publish.md`:
- Caption: **first line = disclosure** (see compliance), then hook line, 3–5 hashtags, CTA.
- Link placement: Instagram → profile link / link-in-bio page / DM automation; YouTube → pinned comment + description top; TikTok → per its affiliate/link rules.
- AI disclosure toggles: Instagram "AI info", YouTube "altered or synthetic content", TikTok AI-generated label — when footage mode B/C shows realistic people or scenes.
- Save the final caption to `caption.txt` (first line = disclosure).
- **Instagram** (needs `IG_ACCESS_TOKEN`, `IG_USER_ID`; setup in `references/instagram-setup.md`):
  ```
  S=.claude/skills/shopping-shorts/scripts
  python3 $S/instagram_publish.py limit                         # quota left
  python3 $S/instagram_publish.py reel shorts/<dir>/final.mp4 --caption-file shorts/<dir>/caption.txt --dry-run
  python3 $S/instagram_publish.py reel shorts/<dir>/final.mp4 --caption-file shorts/<dir>/caption.txt --thumb-offset 1.5
  ```
  Always show the dry-run to the user and get an explicit "올려" before the real run; pass `--yes` only after that. The script refuses captions whose first line lacks a disclosure, uploads the file directly (resumable upload, no public hosting needed), waits for processing, publishes, and appends to `shorts/log.csv`.
  Token expires 60 days after issue/refresh: run `instagram_publish.py refresh` at least monthly (token must be ≥24h old).
- **YouTube Shorts** (setup in `references/youtube-setup.md`; save title/description/tags to `youtube.json`, description line 1 = disclosure, no URLs):
  ```
  python3 $S/youtube_publish.py upload shorts/<dir>/final.mp4 --meta shorts/<dir>/youtube.json --dry-run
  python3 $S/youtube_publish.py upload shorts/<dir>/final.mp4 --meta shorts/<dir>/youtube.json [--synthetic]
  ```
  Same confirmation rule as Instagram. `--synthetic` when footage is realistic AI-generated. Marks paid promotion by default. Uploads from an un-audited API project are locked private.
- **TikTok** (setup in `references/tiktok-setup.md`): default `tiktok_publish.py draft final.mp4` uploads to the creator's TikTok inbox; they finish in the app (caption, sound, branded-content + AI toggles). `direct` posts only after the user approves that exact post — TikTok requires express consent per post. Alternative in chat: Higgsfield `tiktok_prepare_publish` (user submits its form).
- `shorts/log.csv` gets a row per Instagram post automatically; add product id and hook used for other platforms by hand — for later comparing which hooks/products perform.

## Unattended mode
`autopilot/autopilot.py` runs this pipeline on a schedule (see `autopilot/README.md`). When invoked by it through `claude -p`, do exactly the file-writing task in the prompt and nothing else: no questions, no confirmations, no extra files.

## Automation boundaries
Automated: sourcing calls, scoring, scripts, prompts, generation, assembly, captions, logs. Human-confirmed: product pick, script, credit spend, publishing. Keep variation per video (different hook, footage, voice line) — template clones are not monetizable on YouTube and look spammy everywhere.
