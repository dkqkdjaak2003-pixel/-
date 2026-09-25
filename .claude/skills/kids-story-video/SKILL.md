---
name: kids-story-video
description: Plan and produce short children's fairy-tale videos (YouTube Shorts / Reels / TikTok) end to end — brief, original story, scene script, image/video prompts, Higgsfield generation, and a publish checklist. Use when the user asks for a kids' story video, fairy tale short, bedtime story video, or 동화 영상.
---

# Kids' story video pipeline

Work in stages. Save each stage to `stories/<slug>/` so later stages read files instead of re-generating context (saves tokens). Stop after each stage marked **(confirm)** and wait for the user.

## 1. Brief (confirm)
Ask only for what is missing:
- Target age (e.g. 2–4, 4–7), language(s), platform, length (Shorts ≤ 60s, long-form 3–8 min)
- Theme/lesson (sharing, bedtime, courage…), recurring character or new one
Write `brief.md`.

## 2. Story
- Write an ORIGINAL story. Public-domain tales (Grimm, Aesop, Andersen) may be retold; do not copy modern copyrighted characters, songs or scripts.
- Structure: hook in first 2 seconds → problem → 2–3 repeatable beats (repetition works for young kids) → gentle resolution → one-line lesson.
- Simple words, short sentences, no fear/violence beyond age level.
Write `story.md`.

## 3. Scene script
Table in `script.md`: `#`, `duration (s)`, `narration`, `on-screen text`, `visual description`, `camera`, `sfx/music cue`. Shorts: 6–10 scenes of 4–8s.
Use `social-media-skills:hook-generator` / `social-media-skills:reels-scripting` for the hook if installed.

## 4. Prompts
`prompts.md`: one character sheet (fixed appearance words reused verbatim in every prompt for consistency), then one image prompt + one image-to-video motion prompt per scene. Keep a single art style line reused verbatim.

## 5. Generate (confirm — costs Higgsfield credits)
If the `higgsfield` plugin/CLI or Higgsfield MCP is available, use `/higgsfield:generate`:
1. Character reference image first (consider `/higgsfield:soul-id` for a recurring character).
2. Scene images, then image-to-video per scene.
Save outputs under `stories/<slug>/assets/`. Report credits used if the tool reports them.
If Higgsfield is not connected, stop and tell the user; do not fake outputs.

## 6. Assemble
If `ffmpeg` exists, concatenate clips in script order, add narration/music tracks the user supplies, burn captions from `script.md`. Otherwise output an edit list for CapCut.

## 7. Publish checklist
Write `publish.md` with title, description, hashtags, thumbnail prompt (`/higgsfield:youtube-thumbnail` if installed), and:
- YouTube: set audience "Made for kids" when the video is directed at children (required by COPPA / YouTube policy; disables comments and personalized ads).
- Disclose realistic altered/synthetic content where the platform requires it.
- YouTube Partner Program "inauthentic content" rule (renamed 15 Jul 2025): template-like, mass-produced videos with little variation are not monetizable — vary story, visuals and narration per episode.
