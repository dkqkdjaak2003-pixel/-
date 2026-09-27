---
name: ad-film
description: Plan and produce a short vertical video ad (15s TVC-style for Reels/Shorts/TikTok and Meta/TikTok ads) for a real product — single-minded proposition, storyboard, AI footage with the real product as reference, packshot, slogan, sound logo, and delivery cuts. Use for 광고 영상, 광고 제작, 제품 광고, TVC, ad creative, 판매자 광고 대행, or portfolio ads. For affiliate review-style shorts use shopping-shorts instead.
---

# Ad film pipeline

An ad sells one idea. Everything in the 15 seconds serves that one line. Save work under `ads/<yyyymmdd>-<slug>/`. Stop at every **(confirm)**.

Stages 1–3 (brief, concepts, conti) belong to the **ad-planner** agent (`.claude/agents/ad-planner.md`): delegate them to it, or follow `references/planning-playbook.md` yourself when the agent is not loaded. Read `references/ad-framework.md` before the brief. Tools are shared with the shopping-shorts skill:
`S=.claude/skills/shopping-shorts/scripts` (`assemble.py`, `sound.py`).

## 1. Brief (confirm) → `brief.md`
- Who pays: own channel (affiliate) or a client (seller/brand). For a client, get written OK on claims and product photos they supply.
- Product facts sheet: name, price, specs **only from the seller's page or the client**, with source and date.
- **Real product photo(s)** — mandatory. No photo, no ad: generated products drift from the real item and that misleads buyers.
- Audience in one sentence, platform(s), deadline, budget in credits.

## 2. Proposition & concept (confirm) → `concept.md`
- Single-minded proposition (one sentence, benefit not feature). e.g. "옷장이 숨을 쉰다".
- Two or three concept routes, each: one-line idea, tone, why it fits. User picks one.
- Slogan (≤12 characters in Korean where possible) and a sound logo cue.

## 3. Storyboard (confirm) → `storyboard.md` + frames
- Structure (15s): Hook 0–2 · Tension 2–5 · Turn 5–8 · Proof/demo 8–12 · Packshot + slogan + sound logo 12–15.
- For each shot: timing, framing, action, VO line, on-screen text, SFX/music cue.
- Keyframes as marker-sketch storyboard images (`gpt_image_2_5`, ~0.25 credits each) — sketches, never photoreal product mock-ups.
- Publish the board as an Artifact page for review.

## 4. Production (confirm — costs credits)
- Import the product photo (`media_import_url` / upload) and pass it as a reference to every shot that shows the product (`seedance_2_5` omni reference, or `marketing_studio_video` with a product id). Shots without the product (hook, tension) can be text-to-video.
- Hook shot at 1080p, others 720p unless the client pays for 1080p.
- VO: record 2–4 takes (`text2speech_v2`, elevenlabs/minimax), transcribe with faster-whisper in the Higgsfield sandbox, keep the most accurate at the target tempo. Cut the edit to VO word timestamps.
- Music/SFX: `sound.py music ... --style trap|tv`, `sound.py sfx`, `sound.py logo` (sound logo). Match a reference reel by numbers when the user gives one (see shopping-shorts SKILL "Reference-reel analysis").

## 5. Packshot & finishing
- Packshot scene: `{"clip": "image:assets/product.png", "bg": "#F5F6F9", "duration": 3}` — real photo on brand colour with a slow push-in; slogan via a caption with `"style": "Slogan"`; sound logo on the cut.
- Disclosure: affiliate → keep the 광고/파트너스 line on screen and first caption line. Client ad run from the client's account → the client's ad, labelled by the ad platform; posted on our account for pay → disclose.
- AI labels: set the platform's AI-generated/altered flag when shots are generated.

## 6. Deliverables → `delivery.md`
- Master 15s 9:16 1080×1920, -14 LUFS.
- 6s bumper cut (hook + proof + packshot), and a 4:5 1080×1350 feed crop if the client runs feed ads.
- Clean version without captions/VO for the client's own edits when agreed.
- Credits spent, model/voice used, facts sources.
