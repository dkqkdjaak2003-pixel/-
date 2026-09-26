#!/usr/bin/env python3
"""Shopping-shorts autopilot: source -> script -> footage -> assemble -> QA -> publish -> track.

Deterministic steps (API calls, ffmpeg, checks, posting) run here. Creative steps
(product pick, script, AI footage) run through headless Claude Code (`claude -p`),
which loads the project skill `shopping-shorts` and the user's Higgsfield MCP.

Usage (from the repository root):
  python3 autopilot/autopilot.py run              # one full cycle (cron this)
  python3 autopilot/autopilot.py status           # jobs and their stage
  python3 autopilot/autopilot.py approve <job>    # review mode: publish a checked job
  python3 autopilot/autopilot.py reject <job> [reason]
  python3 autopilot/autopilot.py report           # pull insights + commission, update learnings
  python3 autopilot/autopilot.py linkpage         # rebuild the link-in-bio page

Every job lives in shorts/<job>/ with job.json holding its stage, so a crashed or
interrupted run resumes where it stopped on the next `run`.
"""
import datetime
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, ".claude", "skills", "shopping-shorts", "scripts")
sys.path.insert(0, SCRIPTS)
import coupang_partners as cp  # noqa: E402
import instagram_publish as ig  # noqa: E402

SHORTS = os.path.join(ROOT, "shorts")
CONFIG = os.path.join(ROOT, "autopilot", "config.json")
STAGES = ["new", "sourced", "scripted", "footage", "assembled", "checked",
          "awaiting_approval", "published", "rejected", "failed"]
ACTIVE = ("new", "sourced", "scripted", "footage", "assembled", "checked")


# ---------- small helpers ----------

def now():
    return datetime.datetime.now()


def load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def config():
    cfg = load(CONFIG)
    if cfg is None:
        sys.exit("autopilot/config.json not found. Copy autopilot/config.example.json and edit it.")
    return cfg


def log(msg):
    line = f"{now().isoformat(timespec='seconds')} {msg}"
    print(line)
    os.makedirs(SHORTS, exist_ok=True)
    with open(os.path.join(SHORTS, "autopilot.log"), "a", encoding="utf-8") as f:
        f.write(line + "\n")


def notify(cfg, msg):
    log("NOTIFY " + msg)
    cmd = cfg.get("notify_cmd")
    if cmd:
        subprocess.run(cmd, shell=True, env={**os.environ, "MESSAGE": msg}, check=False)


def jobs():
    out = []
    for p in sorted(glob.glob(os.path.join(SHORTS, "*", "job.json"))):
        out.append(load(p))
    return out


def job_dir(job):
    return os.path.join(SHORTS, job["id"])


def save_job(job):
    job["updated"] = now().isoformat(timespec="seconds")
    save(os.path.join(job_dir(job), "job.json"), job)


def set_stage(job, stage, note=""):
    job["stage"] = stage
    job.setdefault("history", []).append([now().isoformat(timespec="seconds"), stage, note])
    save_job(job)
    log(f"{job['id']}: {stage} {note}".rstrip())


# ---------- Claude (creative steps) ----------

def claude(cfg, prompt, tools, cwd):
    c = cfg["claude"]
    if not shutil.which(c.get("bin", "claude")):
        raise RuntimeError("Claude Code CLI not found; install it or set claude.bin in config.")
    cmd = [c.get("bin", "claude"), "-p", prompt,
           "--output-format", "json",
           "--max-turns", str(c.get("max_turns", 40)),
           "--allowedTools", ",".join(tools)] + c.get("extra_args", [])
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                       timeout=c.get("timeout_sec", 3600))
    with open(os.path.join(cwd, "claude.log"), "a", encoding="utf-8") as f:
        f.write(f"\n==== {now().isoformat(timespec='seconds')}\n{r.stdout}\n{r.stderr}\n")
    if r.returncode != 0:
        raise RuntimeError(f"claude exited {r.returncode}: {r.stderr[-500:]}")
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return {"result": r.stdout}


def learnings():
    p = os.path.join(SHORTS, "learnings.md")
    return open(p, encoding="utf-8").read() if os.path.exists(p) else "(아직 성과 데이터 없음)"


# ---------- stages ----------

def used_product_ids():
    return {str(j.get("product", {}).get("productId")) for j in jobs() if j.get("product")}


def source(cfg, job):
    """Collect candidates from Coupang Partners and let Claude pick one."""
    state = load(os.path.join(SHORTS, "state.json"), {"rotation": 0})
    niches = cfg["niches"]
    niche = niches[state["rotation"] % len(niches)]
    state["rotation"] += 1
    save(os.path.join(SHORTS, "state.json"), state)

    raw = []
    if "goldbox" in cfg["sources"]:
        raw += cp.items(cp.goldbox())
    if "best" in cfg["sources"]:
        for cid in niche.get("best_category_ids", []):
            raw += cp.items(cp.best(cid, 20))
    if "search" in cfg["sources"] and niche.get("keywords"):
        kw = niche["keywords"][state["rotation"] % len(niche["keywords"])]
        raw += cp.items(cp.search(kw, 10))  # one search call per run (rate limit)

    used, seen, cands = used_product_ids(), set(), []
    for it in raw:
        pid = str(it.get("productId"))
        price = it.get("productPrice") or 0
        if pid in used or pid in seen:
            continue
        if not (cfg["price_min"] <= price <= cfg["price_max"]):
            continue
        if cfg.get("rocket_only") and not it.get("isRocket"):
            continue
        if any(x in (it.get("categoryName") or "") for x in cfg.get("excluded_categories", [])):
            continue
        seen.add(pid)
        cands.append(it)
    if not cands:
        raise RuntimeError(f"no candidates for niche {niche['name']} after filters")
    save(os.path.join(job_dir(job), "candidates.json"), cands[:30])

    prompt = PICK_PROMPT.format(niche=niche["name"], learnings=learnings())
    claude(cfg, prompt, cfg["claude"]["tools"]["write"], job_dir(job))
    pick = load(os.path.join(job_dir(job), "pick.json"))
    chosen = next((c for c in cands if str(c.get("productId")) == str((pick or {}).get("productId"))), None)
    if not chosen:
        raise RuntimeError("pick.json missing or productId not among candidates")

    sub_id = re.sub(r"[^A-Za-z0-9]", "", job["id"])[:30]
    dl = cp.deeplink([chosen["productUrl"]], sub_id)
    link = (dl.get("data") or [{}])[0].get("shortenUrl")
    if not link:
        raise RuntimeError(f"deeplink failed: {dl}")
    chosen.update({"shortenUrl": link, "subId": sub_id, "niche": niche["name"],
                   "fetched_at": now().isoformat(timespec="seconds"),
                   "pick_reason": pick.get("reason", "")})
    links = load(os.path.join(SHORTS, "links.json"), [])
    no = (max([l["no"] for l in links]) + 1) if links else 1
    chosen["link_no"] = no
    job["product"] = chosen
    save(os.path.join(job_dir(job), "product.json"), chosen)
    set_stage(job, "sourced", chosen.get("productName", "")[:40])


def script(cfg, job):
    prompt = SCRIPT_PROMPT.format(disclosure=cfg["disclosure"], link_no=job["product"]["link_no"],
                                  font=cfg.get("font", "Noto Sans KR"), learnings=learnings())
    claude(cfg, prompt, cfg["claude"]["tools"]["write"], job_dir(job))
    spec = load(os.path.join(job_dir(job), "script.json"))
    cap = os.path.join(job_dir(job), "caption.txt")
    if not spec or not spec.get("scenes") or not os.path.exists(cap):
        raise RuntimeError("script.json / caption.txt not produced")
    spec["disclosure"] = cfg["disclosure"]
    spec.setdefault("font", cfg.get("font", "Noto Sans KR"))
    save(os.path.join(job_dir(job), "script.json"), spec)
    set_stage(job, "scripted")


def footage(cfg, job):
    d = job_dir(job)
    spec = load(os.path.join(d, "script.json"))
    missing = [s["clip"] for s in spec["scenes"] if not os.path.exists(os.path.join(d, s["clip"]))]
    if missing and cfg["footage_mode"] == "higgsfield":
        claude(cfg, FOOTAGE_PROMPT, cfg["claude"]["tools"]["footage"], d)
        failed = os.path.join(d, "assets", "FAILED.txt")
        if os.path.exists(failed):
            reason = open(failed, encoding="utf-8").read().strip()
            os.remove(failed)
            raise RuntimeError(f"footage generation failed: {reason}")
        spec = load(os.path.join(d, "script.json"))
        missing = [s["clip"] for s in spec["scenes"] if not os.path.exists(os.path.join(d, s["clip"]))]
    if missing:
        if cfg["footage_mode"] == "inbox":
            if not job.get("inbox_notified"):
                job["inbox_notified"] = True
                save_job(job)
                notify(cfg, f"{job['id']}: 촬영 필요 — shotlist.md 참고해서 {', '.join(missing)} 를 "
                            f"{os.path.relpath(d, ROOT)}/ 에 넣어주세요")
            return False
        raise RuntimeError(f"clips missing after generation: {missing}")
    set_stage(job, "footage")
    return True


def assemble(cfg, job):
    subprocess.run([sys.executable, os.path.join(SCRIPTS, "assemble.py"), job_dir(job)], check=True)
    set_stage(job, "assembled")


def probe(path):
    ff = shutil.which("ffprobe")
    if not ff:
        return {}
    r = subprocess.run([ff, "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height:format=duration", "-of", "json", path],
                       capture_output=True, text=True)
    j = json.loads(r.stdout or "{}")
    st = (j.get("streams") or [{}])[0]
    return {"w": st.get("width"), "h": st.get("height"),
            "dur": float(j.get("format", {}).get("duration", 0))}


def qa(cfg, job):
    d = job_dir(job)
    problems = []
    video = os.path.join(d, "final.mp4")
    caption = open(os.path.join(d, "caption.txt"), encoding="utf-8").read()
    if not os.path.exists(video):
        problems.append("final.mp4 없음")
    else:
        info = probe(video)
        if info and (info["w"], info["h"]) != (1080, 1920):
            problems.append(f"해상도 {info['w']}x{info['h']}")
        if info and not (cfg["min_sec"] <= info["dur"] <= cfg["max_sec"]):
            problems.append(f"길이 {info['dur']:.1f}s")
    first = caption.strip().splitlines()[0] if caption.strip() else ""
    if cfg["disclosure"] not in first:
        problems.append("캡션 첫 줄에 광고 표기 없음")
    text = caption + json.dumps(load(os.path.join(d, "script.json")), ensure_ascii=False)
    for w in cfg.get("banned_phrases", []):
        if w in text:
            problems.append(f"금지 표현: {w}")
    if re.search(r"https?://", caption):
        problems.append("캡션에 URL (인스타에선 클릭 안 됨; 프로필 링크 번호로 안내)")
    job["qa"] = problems
    if problems:
        set_stage(job, "failed", "QA: " + "; ".join(problems))
        notify(cfg, f"{job['id']} QA 실패: {'; '.join(problems)}")
        return
    set_stage(job, "checked")


def posted_today():
    today = now().date().isoformat()
    return sum(1 for j in jobs() if j.get("stage") == "published"
               and (j.get("published_at") or "").startswith(today))


def publish(cfg, job, approved=False):
    if cfg["publish_mode"] != "auto" and not approved:
        set_stage(job, "awaiting_approval")
        notify(cfg, f"{job['id']} 검수 대기: shorts/{job['id']}/final.mp4 확인 후 "
                    f"`python3 autopilot/autopilot.py approve {job['id']}`")
        return
    if posted_today() >= cfg["max_posts_per_day"]:
        log(f"{job['id']}: daily cap reached, will post next run")
        return
    d = job_dir(job)
    caption = open(os.path.join(d, "caption.txt"), encoding="utf-8").read()
    res = ig.publish(caption, video=os.path.join(d, "final.mp4"),
                     thumb_offset=load(os.path.join(d, "script.json")).get("thumb_offset"))
    ig.append_log(os.path.join(SHORTS, "log.csv"), res, os.path.join(d, "final.mp4"), caption)
    job["instagram"] = res
    job["published_at"] = now().isoformat(timespec="seconds")
    links = load(os.path.join(SHORTS, "links.json"), [])
    p = job["product"]
    links.append({"no": p["link_no"], "name": p.get("productName"), "url": p["shortenUrl"],
                  "image": p.get("productImage"), "date": now().date().isoformat(),
                  "job": job["id"]})
    save(os.path.join(SHORTS, "links.json"), links)
    set_stage(job, "published", res.get("permalink", ""))
    linkpage(cfg)
    notify(cfg, f"{job['id']} 게시 완료 {res.get('permalink', '')}")


# ---------- link-in-bio page ----------

def linkpage(cfg):
    lp = cfg.get("linkpage", {})
    if not lp.get("enabled"):
        return
    links = sorted(load(os.path.join(SHORTS, "links.json"), []), key=lambda x: -x["no"])
    esc = lambda s: (s or "").replace("&", "&amp;").replace("<", "&lt;").replace('"', "&quot;")  # noqa: E731
    rows = "\n".join(
        f'<a class="item" data-no="{l["no"]}" href="{esc(l["url"])}" rel="sponsored noopener">'
        f'<span class="no">{l["no"]}</span>'
        + (f'<img src="{esc(l["image"])}" alt="" loading="lazy">' if l.get("image") else "")
        + f'<span class="name">{esc(l["name"])}</span></a>' for l in links)
    html = LINKPAGE_HTML.replace("{{title}}", esc(lp.get("title", "추천템 모음"))) \
        .replace("{{disclosure}}", esc(cfg["disclosure"])).replace("{{rows}}", rows)
    out = os.path.join(ROOT, lp.get("dir", "docs"), "index.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    log(f"linkpage: {len(links)} items -> {os.path.relpath(out, ROOT)}")
    if lp.get("git_push"):
        rel = os.path.relpath(out, ROOT)
        subprocess.run(["git", "add", rel], cwd=ROOT, check=False)
        if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode:
            subprocess.run(["git", "commit", "-m", "Update link page"], cwd=ROOT, check=False)
            subprocess.run(["git", "push"], cwd=ROOT, check=False)


# ---------- performance tracking ----------

def report(cfg):
    rows = []
    for j in jobs():
        if j.get("stage") != "published":
            continue
        m = ig.insights(j["instagram"]["id"], cfg.get("insight_metrics", ig.DEFAULT_METRICS))
        j["metrics"] = {**m, "fetched_at": now().isoformat(timespec="seconds")}
        save_job(j)
        spec = load(os.path.join(job_dir(j), "script.json")) or {}
        rows.append({"job": j["id"], "niche": j["product"].get("niche"),
                     "category": j["product"].get("categoryName"),
                     "price": j["product"].get("productPrice"),
                     "hook": (spec.get("scenes") or [{}])[0].get("caption", ""), **m})
    end = now().date()
    start = end - datetime.timedelta(days=cfg.get("report_days", 30))
    comm = None
    try:
        comm = cp.report("commission", start.strftime("%Y%m%d"), end.strftime("%Y%m%d"))
        save(os.path.join(SHORTS, "reports", f"commission-{end.isoformat()}.json"), comm)
    except (Exception, SystemExit) as e:  # noqa: BLE001 - report path unverified, keep going
        log(f"commission report failed: {e}")
    save(os.path.join(SHORTS, "performance.json"), rows)

    key = lambda r: (r.get("views") or r.get("reach") or 0)  # noqa: E731
    rows.sort(key=key, reverse=True)
    lines = ["# 성과 요약 (자동 생성)", f"기준일 {end.isoformat()}, 게시물 {len(rows)}개", ""]
    fmt = lambda r: (f"- {r['hook']} | {r['niche']}/{r['category']} | {r['price']}원 | "  # noqa: E731
                     f"조회 {r.get('views')} 도달 {r.get('reach')} 저장 {r.get('saved')} 공유 {r.get('shares')}")
    lines += ["## 잘 된 영상 (훅/카테고리 참고)"] + [fmt(r) for r in rows[:5]]
    lines += ["", "## 안 된 영상 (피할 패턴)"] + [fmt(r) for r in rows[-5:][::-1] if rows[:5].count(r) == 0]
    if comm is not None:
        lines += ["", f"## 쿠팡 커미션 원본: shorts/reports/commission-{end.isoformat()}.json"]
    with open(os.path.join(SHORTS, "learnings.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    log(f"report: {len(rows)} posts, learnings.md updated")


# ---------- driver ----------

def advance(cfg, job):
    try:
        if job["stage"] == "new":
            source(cfg, job)
        if job["stage"] == "sourced":
            script(cfg, job)
        if job["stage"] == "scripted":
            if not footage(cfg, job):
                return
        if job["stage"] == "footage":
            assemble(cfg, job)
        if job["stage"] == "assembled":
            qa(cfg, job)
        if job["stage"] == "checked":
            publish(cfg, job)
    except Exception as e:  # noqa: BLE001 - one job failing must not stop the run
        job["retries"] = job.get("retries", 0) + 1
        err = f"{type(e).__name__}: {e}"
        with open(os.path.join(job_dir(job), "error.log"), "a", encoding="utf-8") as f:
            f.write(traceback.format_exc() + "\n")
        if job["retries"] >= cfg.get("max_retries", 2):
            set_stage(job, "failed", err)
            notify(cfg, f"{job['id']} 실패: {err}")
        else:
            save_job(job)
            log(f"{job['id']}: error (retry {job['retries']}): {err}")


def run(cfg):
    lock = os.path.join(SHORTS, ".lock")
    os.makedirs(SHORTS, exist_ok=True)
    if os.path.exists(lock) and now().timestamp() - os.path.getmtime(lock) < 3 * 3600:
        sys.exit("another run is in progress (shorts/.lock)")
    open(lock, "w").close()
    try:
        pending = [j for j in jobs() if j["stage"] in ACTIVE]
        for i in range(max(0, cfg["videos_per_run"] - len(pending))):
            jid = now().strftime("%Y%m%d%H%M") + chr(ord("a") + i)
            job = {"id": jid, "stage": "new", "created": now().isoformat(timespec="seconds")}
            os.makedirs(os.path.join(SHORTS, jid), exist_ok=True)
            save_job(job)
            pending.append(job)
        for job in pending:
            advance(cfg, job)
    finally:
        os.remove(lock)


def find(job_id):
    j = load(os.path.join(SHORTS, job_id, "job.json"))
    if not j:
        sys.exit(f"no job {job_id}")
    return j


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("run", "status", "approve", "reject", "report", "linkpage"):
        sys.exit(__doc__)
    cfg = config()
    cmd = sys.argv[1]
    if cmd == "run":
        run(cfg)
    elif cmd == "status":
        for j in jobs():
            p = j.get("product", {})
            print(f"{j['id']:14} {j['stage']:18} {p.get('link_no', ''):>4} {(p.get('productName') or '')[:40]}")
    elif cmd == "approve":
        j = find(sys.argv[2])
        if j["stage"] != "awaiting_approval":
            sys.exit(f"{j['id']} is {j['stage']}, not awaiting_approval")
        publish(cfg, j, approved=True)
    elif cmd == "reject":
        j = find(sys.argv[2])
        set_stage(j, "rejected", " ".join(sys.argv[3:]))
    elif cmd == "report":
        report(cfg)
    elif cmd == "linkpage":
        linkpage(cfg)


# ---------- prompts ----------

PICK_PROMPT = """You are running unattended inside a shopping-shorts job folder. Use the project skill
`shopping-shorts` rules. Read candidates.json (Coupang Partners API results, niche: {niche}).
Pick ONE product best suited for a 15-30s vertical short: benefit visible within 3 seconds,
solves an everyday problem, broad appeal, low claim risk (no health/medical/efficacy angle).
Past performance notes:
{learnings}
Write pick.json: {{"productId": <id from candidates.json>, "reason": "<one Korean sentence>"}}.
Do not write anything else. Do not invent data."""

SCRIPT_PROMPT = """You are running unattended inside a shopping-shorts job folder. Follow the project skill
`shopping-shorts` stage 3 rules and its references/compliance.md.
Read product.json. Use ONLY facts present there (name, price as listed, rocket delivery, category).
Never claim rankings, lowest price, discounts, reviews, or health/efficacy effects.
Past performance notes (reuse what worked, vary wording; never copy a previous hook verbatim):
{learnings}
Write three files:
1. script.json for assemble.py: {{"scenes": [{{"clip": "assets/s1.mp4", "caption": "<≤14 Korean chars>",
   "duration": <2-5>, "narration": "<Korean line>", "visual": "<English shot description: product,
   action, setting, camera>"}}, ...], "font": "{font}", "thumb_offset": <seconds>}}
   5-7 scenes, total 15-30s. Scene 1 = hook (problem or surprising result). Most scenes show the
   product in use. Last scene = CTA "프로필 링크 {link_no}번".
2. caption.txt — line 1 exactly: {disclosure}
   then a one-line hook, 2-3 lines of plain benefit, "구매 링크: 프로필 링크 → {link_no}번", 3-5 hashtags.
   No URLs.
3. shotlist.md — the same scenes as a filming list for a phone camera (9:16), in Korean."""

FOOTAGE_PROMPT = """You are running unattended inside a shopping-shorts job folder. Follow the project skill
`shopping-shorts` stage 4 option B and stage 5.
Read script.json and product.json. Using the Higgsfield MCP tools:
1. Check balance first. If credits look insufficient for all scenes, write assets/FAILED.txt with the
   reason and stop.
2. Import productImage from product.json as the reference (media_import_url). Keep the product's real
   shape, color and branding; do not change what the product is or does.
3. For each scene generate a 9:16 video clip of the scene's `visual` (image then image-to-video, or a
   product/UGC preset), duration close to the scene's duration. Batch the jobs and wait for them.
4. Download each result to exactly the scene's `clip` path (e.g. assets/s1.mp4) with curl.
5. Generate a Korean voice-over from all `narration` lines in order, save assets/voice.mp3, and set
   "voice": "assets/voice.mp3" in script.json. Keep every other field of script.json unchanged.
Never fabricate files: if a generation fails twice, write assets/FAILED.txt and stop."""

LINKPAGE_HTML = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{title}}</title>
<style>
:root{--bg:#fafafa;--fg:#111;--card:#fff;--line:#e5e5e5;--muted:#666;--accent:#e4405f}
@media (prefers-color-scheme:dark){:root{--bg:#111;--fg:#f2f2f2;--card:#1c1c1c;--line:#2c2c2c;--muted:#aaa}}
body{margin:0;background:var(--bg);color:var(--fg);font-family:system-ui,-apple-system,"Apple SD Gothic Neo","Noto Sans KR",sans-serif}
main{max-width:560px;margin:0 auto;padding:16px}
h1{font-size:20px;margin:8px 0 4px}
.disc{font-size:12px;color:var(--muted);margin:0 0 12px}
input{width:100%;box-sizing:border-box;font-size:18px;padding:12px;border:1px solid var(--line);border-radius:10px;background:var(--card);color:var(--fg)}
.item{display:flex;align-items:center;gap:12px;padding:10px;margin-top:10px;background:var(--card);border:1px solid var(--line);border-radius:12px;color:inherit;text-decoration:none}
.no{min-width:44px;text-align:center;font-weight:700;color:var(--accent)}
.item img{width:56px;height:56px;object-fit:cover;border-radius:8px}
.name{font-size:14px;line-height:1.35}
</style></head><body><main>
<h1>{{title}}</h1>
<p class="disc">{{disclosure}}</p>
<input id="q" inputmode="numeric" placeholder="영상에 나온 번호 검색">
{{rows}}
</main>
<script>
document.getElementById('q').addEventListener('input',e=>{const v=e.target.value.trim();
document.querySelectorAll('.item').forEach(a=>{a.style.display=!v||a.dataset.no===v?'':'none'})});
</script></body></html>
"""

if __name__ == "__main__":
    main()
