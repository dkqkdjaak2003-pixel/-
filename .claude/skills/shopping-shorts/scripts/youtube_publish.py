#!/usr/bin/env python3
"""Upload Shorts with the YouTube Data API v3 (standard library only).

Setup (once):
  1. Google Cloud console: enable "YouTube Data API v3", create an OAuth client of type
     "Desktop app", download it as client_secret.json.
  2. Set the OAuth consent screen to "In production" (in "Testing", refresh tokens
     expire after 7 days and scheduled uploads stop).
  3. python3 youtube_publish.py auth --client-secret client_secret.json
     -> opens a browser, saves the refresh token to $YT_TOKEN_FILE.
Note: projects that have not passed the YouTube API compliance audit get every
API upload locked to private. Apply for the audit before relying on public uploads.

Usage:
  youtube_publish.py upload final.mp4 --meta youtube.json [--privacy public] [--synthetic] [--dry-run] [--yes]
  youtube_publish.py stats <video_id> [<video_id> ...]
youtube.json: {"title": "...", "description": "...", "tags": ["..."], "categoryId": "26"}
Vertical/square videos up to 3 minutes are classified as Shorts automatically.
"""
import argparse
import http.server
import json
import os
import secrets
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

TOKEN_FILE = os.environ.get("YT_TOKEN_FILE", os.path.expanduser("~/.config/shopping-shorts/youtube_token.json"))
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = os.environ.get("YT_TOKEN_URL", "https://oauth2.googleapis.com/token")
API = os.environ.get("YT_API_BASE", "https://www.googleapis.com/youtube/v3")
UPLOAD = os.environ.get("YT_UPLOAD_BASE", "https://www.googleapis.com/upload/youtube/v3")
SCOPES = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly"
DISCLOSURE_WORDS = ("광고", "수수료", "협찬", "파트너스")


class APIError(Exception):
    def __init__(self, code, body):
        super().__init__(f"HTTP {code}: {body[:800]}")
        self.code, self.body = code, body


def http(method, url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            return r.status, dict(r.headers), r.read().decode() or "{}"
    except urllib.error.HTTPError as e:
        raise APIError(e.code, e.read().decode(errors="replace")) from None


# ---------- OAuth ----------

def auth(client_secret_path):
    with open(client_secret_path, encoding="utf-8") as f:
        c = json.load(f)
    c = c.get("installed") or c.get("web") or c
    code_box, state = {}, secrets.token_urlsafe(16)

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if q.get("state", [""])[0] == state:
                code_box["code"] = q.get("code", [""])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write("인증 완료. 이 창을 닫아도 됩니다.".encode())

    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    redirect = f"http://127.0.0.1:{srv.server_port}"
    url = AUTH_URL + "?" + urllib.parse.urlencode({
        "client_id": c["client_id"], "redirect_uri": redirect, "response_type": "code",
        "scope": SCOPES, "access_type": "offline", "prompt": "consent", "state": state})
    print("브라우저에서 로그인하세요 (자동으로 안 열리면 아래 주소 복사):\n" + url)
    webbrowser.open(url)
    threading.Thread(target=srv.handle_request, daemon=True).start()
    for _ in range(600):
        if "code" in code_box:
            break
        time.sleep(0.5)
    srv.server_close()
    if not code_box.get("code"):
        sys.exit("No authorization code received.")
    _, _, body = http("POST", TOKEN_URL, urllib.parse.urlencode({
        "code": code_box["code"], "client_id": c["client_id"], "client_secret": c["client_secret"],
        "redirect_uri": redirect, "grant_type": "authorization_code"}).encode(),
        {"Content-Type": "application/x-www-form-urlencoded"})
    tok = json.loads(body)
    if "refresh_token" not in tok:
        sys.exit(f"No refresh_token in response: {body}")
    save_token({"client_id": c["client_id"], "client_secret": c["client_secret"],
                "refresh_token": tok["refresh_token"]})
    print(f"saved {TOKEN_FILE}")


def save_token(t):
    os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(t, f)
    os.chmod(TOKEN_FILE, 0o600)


def access_token():
    if not os.path.exists(TOKEN_FILE):
        sys.exit(f"{TOKEN_FILE} not found. Run `youtube_publish.py auth` first.")
    with open(TOKEN_FILE, encoding="utf-8") as f:
        t = json.load(f)
    try:
        _, _, body = http("POST", TOKEN_URL, urllib.parse.urlencode({
            "client_id": t["client_id"], "client_secret": t["client_secret"],
            "refresh_token": t["refresh_token"], "grant_type": "refresh_token"}).encode(),
            {"Content-Type": "application/x-www-form-urlencoded"})
    except APIError as e:
        if "invalid_grant" in e.body:
            sys.exit("Refresh token expired or revoked. Re-run `auth` (and set the consent "
                     "screen to production so it stops expiring every 7 days).")
        raise
    return json.loads(body)["access_token"]


# ---------- upload ----------

def check_meta(meta):
    title, desc = meta.get("title", ""), meta.get("description", "")
    if not title or len(title) > 100 or "<" in title or ">" in title:
        sys.exit("title must be 1-100 chars without < >")
    if len(desc.encode()) > 5000:
        sys.exit("description exceeds 5000 bytes")
    first = desc.strip().splitlines()[0] if desc.strip() else ""
    if not any(w in first for w in DISCLOSURE_WORDS):
        sys.exit("Description first line has no ad disclosure. Aborting.")


def upload(video, meta, privacy="public", synthetic=False, paid_promotion=True):
    """Resumable upload. Returns {"id", "url", "privacy"}."""
    check_meta(meta)
    tok = access_token()
    body = {
        "snippet": {"title": meta["title"], "description": meta["description"],
                    "tags": meta.get("tags", []), "categoryId": str(meta.get("categoryId", "26")),
                    "defaultLanguage": "ko"},
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False,
                   "containsSyntheticMedia": bool(synthetic)},
    }
    parts = ["snippet", "status"]
    if paid_promotion:
        body["paidProductPlacementDetails"] = {"hasPaidProductPlacement": True}
        parts.append("paidProductPlacementDetails")
    size = os.path.getsize(video)

    def start(parts, body):
        url = f"{UPLOAD}/videos?uploadType=resumable&part={','.join(parts)}"
        return http("POST", url, json.dumps(body).encode(), {
            "Authorization": f"Bearer {tok}", "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(size)})

    try:
        _, headers, _ = start(parts, body)
    except APIError as e:
        if paid_promotion and e.code == 400:
            print(f"paidProductPlacementDetails rejected, retrying without it: {e}", file=sys.stderr)
            body.pop("paidProductPlacementDetails")
            parts.remove("paidProductPlacementDetails")
            _, headers, _ = start(parts, body)
        else:
            raise
    location = headers.get("Location") or headers.get("location")
    if not location:
        raise APIError(0, f"no upload Location header: {headers}")
    with open(video, "rb") as f:
        blob = f.read()
    _, _, resp = http("PUT", location, blob, {"Authorization": f"Bearer {tok}",
                                              "Content-Type": "video/mp4"})
    v = json.loads(resp)
    return {"id": v["id"], "url": f"https://www.youtube.com/shorts/{v['id']}",
            "privacy": v.get("status", {}).get("privacyStatus", privacy)}


def stats(ids):
    tok = access_token()
    url = f"{API}/videos?part=statistics,status&id={','.join(ids)}"
    _, _, body = http("GET", url, headers={"Authorization": f"Bearer {tok}"})
    out = {}
    for it in json.loads(body).get("items", []):
        s = it.get("statistics", {})
        out[it["id"]] = {"views": int(s.get("viewCount", 0)), "likes": int(s.get("likeCount", 0)),
                         "comments": int(s.get("commentCount", 0)),
                         "privacy": it.get("status", {}).get("privacyStatus")}
    return out


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    a_ = sub.add_parser("auth")
    a_.add_argument("--client-secret", required=True)
    u = sub.add_parser("upload")
    u.add_argument("video")
    u.add_argument("--meta", required=True)
    u.add_argument("--privacy", default="public", choices=["public", "unlisted", "private"])
    u.add_argument("--synthetic", action="store_true", help="realistic AI-generated/altered content")
    u.add_argument("--no-paid-promotion", action="store_true")
    u.add_argument("--dry-run", action="store_true")
    u.add_argument("--yes", action="store_true")
    s = sub.add_parser("stats")
    s.add_argument("ids", nargs="+")
    a = p.parse_args()

    if a.cmd == "auth":
        auth(a.client_secret)
    elif a.cmd == "stats":
        print(json.dumps(stats(a.ids), ensure_ascii=False, indent=2))
    else:
        with open(a.meta, encoding="utf-8") as f:
            meta = json.load(f)
        check_meta(meta)
        print(f"title: {meta['title']}\n---- description ----\n{meta['description']}\n--------------------")
        print(f"video: {a.video} privacy={a.privacy} synthetic={a.synthetic} "
              f"paid_promotion={not a.no_paid_promotion}")
        if a.dry_run:
            print("dry run: nothing sent.")
            return
        if not a.yes and input("Upload now? [y/N] ").strip().lower() != "y":
            sys.exit("Cancelled.")
        r = upload(a.video, meta, a.privacy, a.synthetic, not a.no_paid_promotion)
        print(f"uploaded: {r['id']} {r['url']} ({r['privacy']})")


if __name__ == "__main__":
    main()
