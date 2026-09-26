#!/usr/bin/env python3
"""TikTok Content Posting API client (standard library only).

Two modes:
  draft  (default, scope video.upload): uploads the video to the creator's TikTok
         inbox. The creator opens the TikTok notification, adds sound/caption and
         posts. Fits TikTok's rule that the user expressly consents to each post.
  direct (scope video.publish): posts to the profile. Only run it after the user
         reviewed this exact video and caption and said yes (autopilot `approve`).
Unaudited API clients: posts are private-only (SELF_ONLY) and the account must be
private; apply for TikTok's audit before relying on public posts.

Env: TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, TIKTOK_TOKEN_FILE (default
~/.config/shopping-shorts/tiktok_token.json), TIKTOK_API_BASE (tests).

Usage:
  tiktok_publish.py auth-url --redirect-uri https://<your link page>/     # open it, approve
  tiktok_publish.py auth --redirect-uri https://<same>/ --code <code from the redirected URL>
  tiktok_publish.py creator                                               # nickname, privacy options, max duration
  tiktok_publish.py draft final.mp4
  tiktok_publish.py direct final.mp4 --caption-file tiktok.txt --privacy PUBLIC_TO_EVERYONE [--aigc] [--yes]
  tiktok_publish.py status <publish_id>
"""
import argparse
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = os.environ.get("TIKTOK_API_BASE", "https://open.tiktokapis.com").rstrip("/")
AUTH = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_FILE = os.environ.get("TIKTOK_TOKEN_FILE",
                            os.path.expanduser("~/.config/shopping-shorts/tiktok_token.json"))
DISCLOSURE_WORDS = ("광고", "수수료", "협찬", "파트너스")
MIN_CHUNK, MAX_CHUNK = 5 * 1024 * 1024, 64 * 1024 * 1024


class APIError(Exception):
    pass


def http(method, url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        raise APIError(f"HTTP {e.code} {url.split('?')[0]}: {e.read().decode(errors='replace')[:800]}") from None


def client():
    k, s = os.environ.get("TIKTOK_CLIENT_KEY"), os.environ.get("TIKTOK_CLIENT_SECRET")
    if not k or not s:
        sys.exit("TIKTOK_CLIENT_KEY / TIKTOK_CLIENT_SECRET are not set.")
    return k, s


def token_request(params):
    k, s = client()
    body = urllib.parse.urlencode({"client_key": k, "client_secret": s, **params}).encode()
    t = http("POST", f"{API}/v2/oauth/token/", body, {"Content-Type": "application/x-www-form-urlencoded"})
    if "access_token" not in t:
        raise APIError(f"token error: {t}")
    t["obtained_at"] = int(time.time())
    os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(t, f)
    os.chmod(TOKEN_FILE, 0o600)
    return t


def access_token():
    if not os.path.exists(TOKEN_FILE):
        sys.exit(f"{TOKEN_FILE} not found. Run `auth-url` then `auth`.")
    with open(TOKEN_FILE, encoding="utf-8") as f:
        t = json.load(f)
    # access tokens last 24h, refresh tokens 365 days; refresh with a 10 min margin
    if time.time() > t["obtained_at"] + int(t.get("expires_in", 86400)) - 600:
        t = token_request({"grant_type": "refresh_token", "refresh_token": t["refresh_token"]})
    return t["access_token"]


def api(path, body):
    r = http("POST", f"{API}{path}", json.dumps(body).encode(), {
        "Authorization": f"Bearer {access_token()}", "Content-Type": "application/json; charset=UTF-8"})
    err = r.get("error", {})
    if err.get("code") not in (None, "ok"):
        raise APIError(f"{path}: {err}")
    return r.get("data", {})


def creator_info():
    return api("/v2/post/publish/creator_info/query/", {})


def source_info(size):
    chunk = size if size < MIN_CHUNK else min(MAX_CHUNK, size)
    count = max(1, size // chunk)
    return {"source": "FILE_UPLOAD", "video_size": size, "chunk_size": chunk,
            "total_chunk_count": count}, chunk, count


def put_chunks(upload_url, video, size, chunk, count):
    with open(video, "rb") as f:
        for i in range(count):
            start = i * chunk
            end = size - 1 if i == count - 1 else start + chunk - 1  # last chunk takes the remainder
            f.seek(start)
            blob = f.read(end - start + 1)
            req = urllib.request.Request(upload_url, data=blob, method="PUT", headers={
                "Content-Type": "video/mp4", "Content-Length": str(len(blob)),
                "Content-Range": f"bytes {start}-{end}/{size}"})
            try:
                urllib.request.urlopen(req, timeout=600).read()
            except urllib.error.HTTPError as e:
                raise APIError(f"chunk {i + 1}/{count} failed: HTTP {e.code} {e.read()[:300]!r}") from None


def draft(video):
    """Upload to the creator's inbox. Returns {"publish_id", "mode"}."""
    size = os.path.getsize(video)
    src, chunk, count = source_info(size)
    d = api("/v2/post/publish/inbox/video/init/", {"source_info": src})
    put_chunks(d["upload_url"], video, size, chunk, count)
    return {"publish_id": d["publish_id"], "mode": "draft"}


def check_caption(caption):
    first = caption.strip().splitlines()[0] if caption.strip() else ""
    if not any(w in first for w in DISCLOSURE_WORDS):
        sys.exit("Caption first line has no ad disclosure. Aborting.")
    if len(caption) > 2200:
        sys.exit("Caption over 2200 characters.")


def direct(video, caption, privacy, aigc=False, allow_comment=True, cover_ms=1000):
    """Post to the profile. Caller must have the user's explicit consent for this post."""
    check_caption(caption)
    info = creator_info()
    options = info.get("privacy_level_options", [])
    if privacy not in options:
        raise APIError(f"privacy {privacy} not allowed for this account now; options: {options}")
    size = os.path.getsize(video)
    src, chunk, count = source_info(size)
    post = {"title": caption, "privacy_level": privacy,
            "disable_comment": not allow_comment or bool(info.get("comment_disabled")),
            "disable_duet": True, "disable_stitch": True,
            "video_cover_timestamp_ms": cover_ms,
            "brand_content_toggle": True,     # affiliate commission = promoting a third-party product
            "brand_organic_toggle": False,
            "is_aigc": bool(aigc)}
    d = api("/v2/post/publish/video/init/", {"post_info": post, "source_info": src})
    put_chunks(d["upload_url"], video, size, chunk, count)
    return {"publish_id": d["publish_id"], "mode": "direct", "creator": info.get("creator_nickname")}


def status(publish_id):
    return api("/v2/post/publish/status/fetch/", {"publish_id": publish_id})


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("auth-url")
    u.add_argument("--redirect-uri", required=True)
    u.add_argument("--scopes", default="user.info.basic,video.upload,video.publish")
    a_ = sub.add_parser("auth")
    a_.add_argument("--redirect-uri", required=True)
    a_.add_argument("--code", required=True)
    sub.add_parser("creator")
    d = sub.add_parser("draft")
    d.add_argument("video")
    x = sub.add_parser("direct")
    x.add_argument("video")
    x.add_argument("--caption-file", required=True)
    x.add_argument("--privacy", required=True,
                   choices=["PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS", "FOLLOWER_OF_CREATOR", "SELF_ONLY"])
    x.add_argument("--aigc", action="store_true")
    x.add_argument("--yes", action="store_true")
    s = sub.add_parser("status")
    s.add_argument("publish_id")
    a = p.parse_args()

    if a.cmd == "auth-url":
        k, _ = client()
        print(AUTH + "?" + urllib.parse.urlencode({
            "client_key": k, "scope": a.scopes, "response_type": "code",
            "redirect_uri": a.redirect_uri, "state": secrets.token_urlsafe(12)}))
        print("\nApprove, then copy the `code` parameter from the address bar of the redirected page.")
    elif a.cmd == "auth":
        t = token_request({"grant_type": "authorization_code", "code": urllib.parse.unquote(a.code),
                           "redirect_uri": a.redirect_uri})
        print(f"saved {TOKEN_FILE} (scopes: {t.get('scope')})")
    elif a.cmd == "creator":
        print(json.dumps(creator_info(), ensure_ascii=False, indent=2))
    elif a.cmd == "draft":
        print(json.dumps(draft(a.video), ensure_ascii=False))
        print("Open the TikTok app notification to finish and post.")
    elif a.cmd == "direct":
        caption = open(a.caption_file, encoding="utf-8").read().strip()
        info = creator_info()
        print(f"account: {info.get('creator_nickname')} (@{info.get('creator_username')})")
        print(f"max duration: {info.get('max_video_post_duration_sec')}s  privacy: {a.privacy}  "
              f"branded content: on  AI-generated: {a.aigc}\n---- caption ----\n{caption}\n-----------------")
        if not a.yes and input("Post this video to TikTok now? [y/N] ").strip().lower() != "y":
            sys.exit("Cancelled.")
        print(json.dumps(direct(a.video, caption, a.privacy, a.aigc), ensure_ascii=False))
    else:
        print(json.dumps(status(a.publish_id), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
