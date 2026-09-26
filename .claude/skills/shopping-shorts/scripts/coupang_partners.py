#!/usr/bin/env python3
"""Coupang Partners Open API client (standard library only).

Keys come from env vars COUPANG_ACCESS_KEY / COUPANG_SECRET_KEY. Keys are issued
in the Partners portal only after the account passes final approval.

Usage:
  coupang_partners.py search "무선 청소기" --limit 10
  coupang_partners.py goldbox
  coupang_partners.py best 1001 --limit 20
  coupang_partners.py deeplink https://www.coupang.com/vp/products/123 [--sub-id video01]
  coupang_partners.py report commission 20260901 20260926
  coupang_partners.py sign GET /path "a=1"   # print the Authorization header only

The search endpoint is rate limited (reported as 10 calls/hour); repeated
violations can suspend API access, so results are cached under .cache/.
subId (alphanumeric) tags a deeplink so clicks/orders can be told apart per video.
The report paths (/reports/{clicks,orders,cancels,commission}) follow the public
SDKs; confirm them in the Partners portal API docs if a call returns 404.
"""
import argparse
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.parse
import urllib.request

DOMAIN = os.environ.get("COUPANG_API_BASE", "https://api-gateway.coupang.com")
BASE = "/v2/providers/affiliate_open_api/apis/openapi/v1"
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
SEARCH_CACHE_TTL = 6 * 3600


def authorization(method, path, query, access_key, secret_key, now=None):
    signed_date = time.strftime("%y%m%dT%H%M%SZ", time.gmtime(now))
    message = signed_date + method + path + query
    signature = hmac.new(secret_key.encode(), message.encode(), hashlib.sha256).hexdigest()
    return (
        f"CEA algorithm=HmacSHA256, access-key={access_key}, "
        f"signed-date={signed_date}, signature={signature}"
    )


def keys():
    ak, sk = os.environ.get("COUPANG_ACCESS_KEY"), os.environ.get("COUPANG_SECRET_KEY")
    if not ak or not sk:
        sys.exit("COUPANG_ACCESS_KEY / COUPANG_SECRET_KEY are not set.")
    return ak, sk


def call(method, path, params=None, body=None):
    ak, sk = keys()
    query = urllib.parse.urlencode(params or {})
    url = DOMAIN + path + ("?" + query if query else "")
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", authorization(method, path, query, ak, sk))
    req.add_header("Content-Type", "application/json;charset=UTF-8")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def cached(name, ttl, fn):
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, hashlib.sha1(name.encode()).hexdigest() + ".json")
    if os.path.exists(path) and time.time() - os.path.getmtime(path) < ttl:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    result = fn()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)
    return result


def items(resp):
    """Normalize product lists from search/goldbox/best responses."""
    data = resp.get("data", [])
    if isinstance(data, dict):
        data = data.get("productData", [])
    return data


def search(keyword, limit=10):
    params = {"keyword": keyword, "limit": limit}
    return cached("search:" + json.dumps(params, ensure_ascii=False), SEARCH_CACHE_TTL,
                  lambda: call("GET", BASE + "/products/search", params))


def goldbox():
    return call("GET", BASE + "/products/goldbox")


def best(category_id, limit=20):
    return call("GET", f"{BASE}/products/bestcategories/{category_id}", {"limit": limit})


def deeplink(urls, sub_id=None):
    body = {"coupangUrls": list(urls)}
    if sub_id:
        body["subId"] = sub_id
    return call("POST", BASE + "/deeplink", body=body)


def report(kind, start, end, sub_id=None):
    params = {"startDate": start, "endDate": end}
    if sub_id:
        params["subId"] = sub_id
    return call("GET", f"{BASE}/reports/{kind}", params)


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("keyword")
    s.add_argument("--limit", type=int, default=10)
    sub.add_parser("goldbox")
    b = sub.add_parser("best")
    b.add_argument("category_id")
    b.add_argument("--limit", type=int, default=20)
    d = sub.add_parser("deeplink")
    d.add_argument("urls", nargs="+")
    d.add_argument("--sub-id")
    r = sub.add_parser("report")
    r.add_argument("kind", choices=["clicks", "orders", "cancels", "commission"])
    r.add_argument("start", help="yyyymmdd")
    r.add_argument("end", help="yyyymmdd")
    r.add_argument("--sub-id")
    g = sub.add_parser("sign")
    g.add_argument("method")
    g.add_argument("path")
    g.add_argument("query", nargs="?", default="")
    a = p.parse_args()

    if a.cmd == "search":
        out = search(a.keyword, a.limit)
    elif a.cmd == "goldbox":
        out = goldbox()
    elif a.cmd == "best":
        out = best(a.category_id, a.limit)
    elif a.cmd == "deeplink":
        out = deeplink(a.urls, a.sub_id)
    elif a.cmd == "report":
        out = report(a.kind, a.start, a.end, a.sub_id)
    else:
        ak, sk = keys()
        print(authorization(a.method, a.path, a.query, ak, sk))
        return
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
