#!/usr/bin/env python3
"""Publish a Reel through the Instagram API with Instagram Login (standard library only).

Env:
  IG_ACCESS_TOKEN   long-lived token with instagram_business_content_publish
  IG_USER_ID        Instagram professional account id (see `me`)
  IG_API_VERSION    default v23.0
  IG_GRAPH_BASE     default https://graph.instagram.com (override for tests)

Usage:
  instagram_publish.py me                       # account id / username check
  instagram_publish.py limit                    # quota used in the 24h window
  instagram_publish.py refresh                  # extend token another 60 days
  instagram_publish.py reel shorts/<dir>/final.mp4 --caption-file shorts/<dir>/caption.txt [--dry-run]
  instagram_publish.py reel --video-url https://.../final.mp4 --caption "..."
  instagram_publish.py insights <media_id> [--metrics views,reach,likes,comments,shares,saved]

Publishing is public and cannot be undone by this script. `reel` refuses to run
unless the caption's first line carries an ad disclosure, and asks for
confirmation unless --yes is given.
"""
import argparse
import csv
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

VERSION = os.environ.get("IG_API_VERSION", "v23.0")
GRAPH = os.environ.get("IG_GRAPH_BASE", "https://graph.instagram.com").rstrip("/")
DISCLOSURE_WORDS = ("광고", "수수료", "협찬", "파트너스")
MAX_BYTES = 300 * 1024 * 1024
DEFAULT_METRICS = ("views", "reach", "likes", "comments", "shares", "saved")


def token():
    t = os.environ.get("IG_ACCESS_TOKEN")
    if not t:
        sys.exit("IG_ACCESS_TOKEN is not set.")
    return t


def user_id():
    u = os.environ.get("IG_USER_ID")
    if not u:
        sys.exit("IG_USER_ID is not set. Run `instagram_publish.py me` to find it.")
    return u


def request(method, url, params=None, data=None, headers=None):
    params = dict(params or {})
    if url.startswith(GRAPH):
        params.setdefault("access_token", token())
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        sys.exit(f"HTTP {e.code} {method} {url.split('?')[0]}\n{body}")


class APIError(Exception):
    pass


def request_soft(method, url, params=None):
    try:
        return request(method, url, params)
    except SystemExit as e:
        raise APIError(str(e)) from None


def api(method, path, **params):
    url = f"{GRAPH}/{VERSION}/{path}"
    if method == "POST":
        body = urllib.parse.urlencode(params).encode()
        return request(method, url, data=body,
                       headers={"Content-Type": "application/x-www-form-urlencoded"})
    return request(method, url, params)


def check_caption(caption):
    first = caption.strip().splitlines()[0] if caption.strip() else ""
    if not any(w in first for w in DISCLOSURE_WORDS):
        sys.exit("Caption first line has no ad disclosure (광고/수수료/협찬/파트너스). "
                 "Korea FTC guideline requires it at the start. Aborting.")
    if len(caption) > 2200:
        sys.exit(f"Caption is {len(caption)} chars; Instagram allows 2200.")


def wait_ready(container_id, timeout=600, interval=15):
    deadline = time.time() + timeout
    while True:
        st = api("GET", container_id, fields="status_code,status")
        code = st.get("status_code")
        print(f"container {container_id}: {code}")
        if code == "FINISHED":
            return
        if code in ("ERROR", "EXPIRED"):
            sys.exit(f"Container failed: {json.dumps(st, ensure_ascii=False)}")
        if time.time() > deadline:
            sys.exit("Timed out waiting for video processing; container id kept above.")
        time.sleep(interval)


def publish_reel(a):
    caption = a.caption or ""
    if a.caption_file:
        with open(a.caption_file, encoding="utf-8") as f:
            caption = f.read()
    check_caption(caption)
    if not a.video and not a.video_url:
        sys.exit("Give a local video path or --video-url.")
    if a.video:
        if not a.video.lower().endswith((".mp4", ".mov")):
            sys.exit("Reels accept MP4/MOV only.")
        size = os.path.getsize(a.video)
        if size > MAX_BYTES:
            sys.exit(f"File is {size / 1e6:.0f} MB; limit is 300 MB.")

    print("---- caption ----\n" + caption + "\n-----------------")
    print(f"video: {a.video or a.video_url}  share_to_feed={not a.no_feed}")
    if a.dry_run:
        print("dry run: nothing sent.")
        return
    if not a.yes and input("Publish publicly now? [y/N] ").strip().lower() != "y":
        sys.exit("Cancelled.")

    result = publish(caption, video=a.video, video_url=a.video_url,
                     thumb_offset=a.thumb_offset, share_to_feed=not a.no_feed)
    print(f"published: {result['id']} {result['permalink']}")
    append_log(a.log, result, a.video or a.video_url, caption)


def publish(caption, video=None, video_url=None, thumb_offset=None, share_to_feed=True):
    """Create, upload, wait, publish. Returns {"id", "permalink"}."""
    check_caption(caption)
    params = {"media_type": "REELS", "caption": caption,
              "share_to_feed": "true" if share_to_feed else "false"}
    if thumb_offset is not None:
        params["thumb_offset"] = int(thumb_offset * 1000)
    uid = user_id()
    if video_url:
        params["video_url"] = video_url
        container = api("POST", f"{uid}/media", **params)
    else:
        params["upload_type"] = "resumable"
        container = api("POST", f"{uid}/media", **params)
        with open(video, "rb") as f:
            blob = f.read()
        upload_uri = container.get("uri") or \
            f"https://rupload.facebook.com/ig-api-upload/{VERSION}/{container['id']}"
        request("POST", upload_uri, data=blob, headers={
            "Authorization": f"OAuth {token()}",
            "Content-Type": "application/octet-stream",
            "offset": "0",
            "file_size": str(len(blob)),
        })
    cid = container["id"]
    wait_ready(cid)
    media = api("POST", f"{uid}/media_publish", creation_id=cid)
    link = api("GET", media["id"], fields="permalink").get("permalink", "")
    return {"id": media["id"], "permalink": link}


def insights(media_id, metrics=DEFAULT_METRICS):
    """Per-metric fetch so one unsupported metric does not fail the rest."""
    out = {}
    for m in metrics:
        try:
            resp = request_soft("GET", f"{GRAPH}/{VERSION}/{media_id}/insights", {"metric": m})
            out[m] = resp["data"][0]["values"][0]["value"]
        except Exception as e:  # noqa: BLE001 - metric names change between API versions
            out[m] = None
            print(f"insight {m}: {e}", file=sys.stderr)
    return out


def append_log(path, result, video, caption):
    if not path:
        return
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    new = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["date", "platform", "media_id", "permalink", "video", "caption_first_line"])
        w.writerow([datetime.datetime.now().isoformat(timespec="seconds"), "instagram",
                    result["id"], result["permalink"], video, caption.strip().splitlines()[0]])


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("me")
    sub.add_parser("limit")
    sub.add_parser("refresh")
    i = sub.add_parser("insights")
    i.add_argument("media_id")
    i.add_argument("--metrics", default=",".join(DEFAULT_METRICS))
    r = sub.add_parser("reel")
    r.add_argument("video", nargs="?")
    r.add_argument("--video-url")
    r.add_argument("--caption")
    r.add_argument("--caption-file")
    r.add_argument("--thumb-offset", type=float, help="cover frame, seconds")
    r.add_argument("--no-feed", action="store_true", help="Reels tab only")
    r.add_argument("--log", default="shorts/log.csv")
    r.add_argument("--dry-run", action="store_true")
    r.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    a = p.parse_args()

    if a.cmd == "me":
        out = api("GET", "me", fields="user_id,username,account_type")
    elif a.cmd == "limit":
        out = api("GET", f"{user_id()}/content_publishing_limit", fields="quota_usage,config")
    elif a.cmd == "refresh":
        out = request("GET", f"{GRAPH}/refresh_access_token", {"grant_type": "ig_refresh_token"})
        if "expires_in" in out:
            out["expires_at"] = (datetime.datetime.now() +
                                 datetime.timedelta(seconds=out["expires_in"])).isoformat(timespec="minutes")
        print("Save the new access_token in IG_ACCESS_TOKEN.", file=sys.stderr)
    elif a.cmd == "insights":
        out = insights(a.media_id, a.metrics.split(","))
    else:
        publish_reel(a)
        return
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
