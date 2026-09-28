#!/usr/bin/env python3
"""Telegram bot for the autopilot: alerts, video preview, approve/reject buttons, commands.

Bot API: https://core.telegram.org/bots/api  (standard library only)

Env (autopilot/.env):
  TELEGRAM_BOT_TOKEN   from @BotFather (/newbot)
  TELEGRAM_CHAT_ID     your chat id; only this chat can control the bot
  TELEGRAM_API_BASE    optional, default https://api.telegram.org (tests use a mock)

  python3 autopilot/telegram_bot.py chatid       # after sending /start to your bot: prints chat ids
  python3 autopilot/telegram_bot.py test         # sends a test message
  python3 autopilot/autopilot.py telegram        # long-poll: buttons + /status /run /report ...

Limits (Bot API docs): text 4096 chars, caption 1024 chars, bot uploads up to 50 MB,
callback_data 1-64 bytes. getUpdates does not work while a webhook is set.
"""
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
import uuid

TEXT_MAX, CAPTION_MAX, UPLOAD_MAX = 4096, 1024, 50 * 1024 * 1024


def _base():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set (autopilot/.env)")
    return f"{os.environ.get('TELEGRAM_API_BASE', 'https://api.telegram.org').rstrip('/')}/bot{token}"


def enabled():
    return bool(os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"))


def call(method, params=None, files=None, timeout=60):
    url = f"{_base()}/{method}"
    if files:
        boundary = uuid.uuid4().hex
        body = b""
        for k, v in (params or {}).items():
            v = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v)
            body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n"
                     f"{v}\r\n").encode()
        for k, path in files.items():
            ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
            with open(path, "rb") as f:
                data = f.read()
            body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"; "
                     f"filename=\"{os.path.basename(path)}\"\r\nContent-Type: {ctype}\r\n\r\n").encode()
            body += data + b"\r\n"
        body += f"--{boundary}--\r\n".encode()
        req = urllib.request.Request(url, body, {"Content-Type": f"multipart/form-data; boundary={boundary}"})
    else:
        req = urllib.request.Request(url, json.dumps(params or {}).encode(),
                                     {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            res = json.load(r)
    except urllib.error.HTTPError as e:
        res = json.loads(e.read() or b"{}")
    if not res.get("ok"):
        raise RuntimeError(f"telegram {method}: {res.get('error_code')} {res.get('description')}")
    return res["result"]


def buttons(job_id):
    return {"inline_keyboard": [[{"text": "✅ 승인·게시", "callback_data": f"approve:{job_id}"},
                                 {"text": "❌ 반려", "callback_data": f"reject:{job_id}"}]]}


def send(text, chat_id=None, markup=None):
    p = {"chat_id": chat_id or os.environ["TELEGRAM_CHAT_ID"], "text": text[:TEXT_MAX],
         "disable_web_page_preview": True}
    if markup:
        p["reply_markup"] = markup
    return call("sendMessage", p)


def send_video(path, caption="", markup=None, chat_id=None):
    """Upload a video (<=50 MB); larger files fall back to a text message."""
    chat_id = chat_id or os.environ["TELEGRAM_CHAT_ID"]
    if not os.path.exists(path) or os.path.getsize(path) > UPLOAD_MAX:
        return send(caption + f"\n(영상 첨부 불가: {os.path.basename(path)})", chat_id, markup)
    p = {"chat_id": chat_id, "caption": caption[:CAPTION_MAX], "supports_streaming": "true"}
    if markup:
        p["reply_markup"] = markup
    return call("sendVideo", p, files={"video": path}, timeout=300)


def updates(offset=None, timeout=50):
    p = {"timeout": timeout, "allowed_updates": ["message", "callback_query"]}
    if offset is not None:
        p["offset"] = offset
    return call("getUpdates", p, timeout=timeout + 10)


def poll(handle, once=False):
    """Long-poll and pass (kind, data, chat_id, update) to handle(); only TELEGRAM_CHAT_ID is served.

    kind is "command" (data = "/status arg") or "button" (data = callback_data).
    handle returns reply text (or None)."""
    owner = str(os.environ["TELEGRAM_CHAT_ID"])
    offset = None
    while True:
        try:
            batch = updates(offset, timeout=0 if once else 50)
        except (OSError, RuntimeError) as e:  # network blip or API error: wait and retry
            if once:
                raise
            print(f"telegram poll error: {e}", file=sys.stderr)
            time.sleep(15)
            continue
        for u in batch:
            offset = u["update_id"] + 1
            if "callback_query" in u:
                q = u["callback_query"]
                chat = str(q["message"]["chat"]["id"])
                if chat != owner:
                    call("answerCallbackQuery", {"callback_query_id": q["id"], "text": "권한 없음"})
                    continue
                call("answerCallbackQuery", {"callback_query_id": q["id"], "text": "처리 중…"})
                # remove the buttons so the same job is not approved twice
                call("editMessageReplyMarkup", {"chat_id": chat, "message_id": q["message"]["message_id"],
                                                "reply_markup": {"inline_keyboard": []}})
                reply = handle("button", q.get("data", ""), chat, u)
            elif "message" in u and (u["message"].get("text") or "").startswith("/"):
                chat = str(u["message"]["chat"]["id"])
                if chat != owner:
                    continue
                reply = handle("command", u["message"]["text"], chat, u)
            else:
                continue
            if reply:
                send(reply, chat)
        if once:
            if offset is not None:
                updates(offset, timeout=0)  # confirm the processed updates
            return


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "chatid":
        seen = {}
        for u in updates(timeout=0):
            m = u.get("message") or u.get("callback_query", {}).get("message") or {}
            c = m.get("chat")
            if c:
                seen[c["id"]] = c.get("username") or c.get("title") or c.get("first_name")
        if not seen:
            sys.exit("no messages yet: open your bot in Telegram, press Start (or send /start), then rerun")
        for cid, name in seen.items():
            print(f"TELEGRAM_CHAT_ID={cid}   # {name}")
    elif cmd == "test":
        send("✅ 오토파일럿 텔레그램 연결 완료")
        print("sent")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
