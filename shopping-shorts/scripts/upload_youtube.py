"""Upload jobs/<slug>/out/final.mp4 to YouTube as PRIVATE.

First time (사장님이 직접, 브라우저에서 "허용"):
    python scripts/upload_youtube.py --login
Then:
    python scripts/upload_youtube.py jobs/<slug>

Secrets live outside the repo/OneDrive:
    %USERPROFILE%\\.shopping-shorts-secrets\\client_secret.json  (Google Cloud OAuth client, Desktop app)
    %USERPROFILE%\\.shopping-shorts-secrets\\token.json          (created by --login)
Override with SHOPPING_SHORTS_SECRETS env var.
"""
import argparse, json, os, sys
from datetime import date
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
SECRETS = Path(os.environ.get("SHOPPING_SHORTS_SECRETS", Path.home() / ".shopping-shorts-secrets"))
CLIENT, TOKEN, LOGIN_LOG = SECRETS / "client_secret.json", SECRETS / "token.json", SECRETS / "last_login.txt"


def login():
    from google_auth_oauthlib.flow import InstalledAppFlow
    if not CLIENT.exists():
        sys.exit(f"OAuth 클라이언트 파일이 없습니다: {CLIENT}")
    creds = InstalledAppFlow.from_client_secrets_file(str(CLIENT), SCOPES).run_local_server(port=0)
    TOKEN.write_text(creds.to_json(), encoding="utf-8", newline="\n")
    # OAuth app in "Testing" status: refresh token expires after 7 days
    LOGIN_LOG.write_text(date.today().isoformat() + "\n", encoding="utf-8", newline="\n")
    print(f"로그인 완료. 토큰 저장: {TOKEN}")


def load_creds():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    if not TOKEN.exists():
        print("토큰 없음. 사장님이 먼저 --login 을 실행해야 합니다.")
        sys.exit(2)
    creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    if not creds.valid:
        try:
            creds.refresh(Request())
        except Exception as e:  # expired/revoked refresh token: never open a browser here
            print(f"토큰 갱신 실패({e}). 사장님이 --login 을 다시 실행해야 합니다.")
            sys.exit(2)
        TOKEN.write_text(creds.to_json(), encoding="utf-8", newline="\n")
    return creds


def upload(job_dir):
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    job_dir = Path(job_dir)
    video, result = job_dir / "out" / "final.mp4", job_dir / "out" / "youtube.json"
    if result.exists():
        print(f"이미 업로드됨: {result.read_text(encoding='utf-8').strip()}")
        return
    if not video.exists():
        sys.exit(f"영상 없음: {video} — render.py 먼저 실행")
    yt = json.loads((job_dir / "job.json").read_text(encoding="utf-8"))["youtube"]

    body = {
        "snippet": {
            "title": yt["title"][:100],
            "description": yt.get("description", "")[:5000],
            "tags": yt.get("tags", []),
            "categoryId": str(yt.get("category_id", "22")),
            "defaultLanguage": "ko",
        },
        "status": {
            "privacyStatus": "private",  # 공개 전환은 사장님이 Studio에서 확인 후 직접
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": bool(yt.get("synthetic_media", True)),
        },
    }
    service = build("youtube", "v3", credentials=load_creds(), static_discovery=True)
    req = service.videos().insert(part="snippet,status", body=body,
                                  media_body=MediaFileUpload(str(video), chunksize=-1, resumable=True))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    info = {"video_id": resp["id"], "url": f"https://youtu.be/{resp['id']}", "privacy": "private"}
    result.write_text(json.dumps(info, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"비공개 업로드 완료: {info['url']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job_dir", nargs="?")
    ap.add_argument("--login", action="store_true")
    a = ap.parse_args()
    SECRETS.mkdir(parents=True, exist_ok=True)
    if a.login:
        login()
    elif a.job_dir:
        upload(a.job_dir)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
