#!/usr/bin/env python3
"""Keep the cron's SQLite state in a private R2 bucket, for cloud routines that start from a fresh clone.

    state.py pull   download every state file; fails if one is missing, so a run never starts on empty state
    state.py push   upload every state file, only while R2 still holds the copy this run pulled (If-Match)
    state.py seed   upload local files once, only where the bucket has none yet (If-None-Match: *)

`--data-dir DIR` points at another data directory (default: ../data next to this script), e.g. the laptop runtime's
when seeding. Reads SEO_STATE_R2_URL (https://<account id>.r2.cloudflarestorage.com/<bucket>),
SEO_STATE_R2_ACCESS_KEY_ID and SEO_STATE_R2_SECRET_ACCESS_KEY: an R2 API token with Object Read & Write on that bucket
only. Standard library only; signs requests with AWS Signature Version 4, which R2's S3 API accepts.
"""
import argparse
import datetime
import hashlib
import hmac
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

FILES = ["actions.sqlite", "geo-history.sqlite"]


def sign(method, url, headers, payload_hash, key_id, secret):
    """Return the headers for an AWS SigV4-signed S3 request (region `auto`, as R2 expects)."""
    parts = urllib.parse.urlsplit(url)
    now = datetime.datetime.now(datetime.timezone.utc)
    amz_date, day = now.strftime("%Y%m%dT%H%M%SZ"), now.strftime("%Y%m%d")
    headers = {k.lower(): v for k, v in headers.items()}
    headers.update({"host": parts.netloc, "x-amz-date": amz_date, "x-amz-content-sha256": payload_hash})
    names = sorted(headers)
    canonical = "\n".join([
        method,
        urllib.parse.quote(parts.path, safe="/-_.~"),
        parts.query,
        "".join(f"{n}:{headers[n].strip()}\n" for n in names),
        ";".join(names),
        payload_hash,
    ])
    scope = f"{day}/auto/s3/aws4_request"
    to_sign = "\n".join(["AWS4-HMAC-SHA256", amz_date, scope, hashlib.sha256(canonical.encode()).hexdigest()])
    k = ("AWS4" + secret).encode()
    for part in (day, "auto", "s3", "aws4_request"):
        k = hmac.new(k, part.encode(), hashlib.sha256).digest()
    signature = hmac.new(k, to_sign.encode(), hashlib.sha256).hexdigest()
    headers["authorization"] = (
        f"AWS4-HMAC-SHA256 Credential={key_id}/{scope}, SignedHeaders={';'.join(names)}, Signature={signature}"
    )
    return headers


def request(method, name, body=b"", headers=None):
    """Send a signed request for one object; return (status, response headers, body). Never raises on HTTP errors."""
    base = os.environ["SEO_STATE_R2_URL"].rstrip("/")
    url = f"{base}/{name}"
    headers = dict(headers or {})
    if method == "PUT":
        # urllib would otherwise label the body form-urlencoded, which servers may parse as a form and drop.
        headers["Content-Type"] = "application/octet-stream"
    signed = sign(method, url, headers, hashlib.sha256(body).hexdigest(),
                  os.environ["SEO_STATE_R2_ACCESS_KEY_ID"], os.environ["SEO_STATE_R2_SECRET_ACCESS_KEY"])
    # Python's default user agent is refused by some Cloudflare-fronted hosts (error 1010).
    signed["user-agent"] = "seo-geo-cron-state/1"
    req = urllib.request.Request(url, data=body if method == "PUT" else None, headers=signed, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.headers, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read()


def etag_path(data_dir, name):
    return os.path.join(data_dir, f".{name}.etag")


def pull(data_dir):
    for name in FILES:
        status, headers, body = request("GET", name)
        if status == 404:
            sys.exit(f"state: {name} is not in R2. Seed it from the machine that holds the real file "
                     "(state.py seed --data-dir <dir>); never start a cron run on an empty one.")
        if status != 200:
            sys.exit(f"state: GET {name} returned {status}: {body[:300]!r}")
        with open(os.path.join(data_dir, name), "wb") as f:
            f.write(body)
        with open(etag_path(data_dir, name), "w") as f:
            f.write(headers["ETag"])
        print(f"state: pulled {name} ({len(body)} bytes)")


def push(data_dir):
    for name in FILES:
        if not os.path.exists(etag_path(data_dir, name)):
            sys.exit(f"state: {name} was never pulled in this run; refusing to overwrite R2 blindly. Run pull first.")
        with open(etag_path(data_dir, name)) as f:
            expected = f.read().strip()
        with open(os.path.join(data_dir, name), "rb") as f:
            body = f.read()
        status, headers, resp = request("PUT", name, body, {"If-Match": expected})
        if status == 412:
            sys.exit(f"state: {name} changed in R2 since this run pulled it (another run?). Not overwriting it.")
        if status != 200:
            sys.exit(f"state: PUT {name} returned {status}: {resp[:300]!r}")
        with open(etag_path(data_dir, name), "w") as f:
            f.write(headers["ETag"])
        print(f"state: pushed {name} ({len(body)} bytes)")


def seed(data_dir):
    for name in FILES:
        with open(os.path.join(data_dir, name), "rb") as f:
            body = f.read()
        status, _, resp = request("PUT", name, body, {"If-None-Match": "*"})
        if status == 412:
            print(f"state: {name} already in R2, left as is")
        elif status == 200:
            print(f"state: seeded {name} ({len(body)} bytes)")
        else:
            sys.exit(f"state: PUT {name} returned {status}: {resp[:300]!r}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["pull", "push", "seed"])
    ap.add_argument("--data-dir", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
    a = ap.parse_args()
    missing = [v for v in ("SEO_STATE_R2_URL", "SEO_STATE_R2_ACCESS_KEY_ID", "SEO_STATE_R2_SECRET_ACCESS_KEY")
               if not os.environ.get(v)]
    if missing:
        sys.exit(f"state: {', '.join(missing)} not set in this environment")
    {"pull": pull, "push": push, "seed": seed}[a.command](a.data_dir)


if __name__ == "__main__":
    main()
