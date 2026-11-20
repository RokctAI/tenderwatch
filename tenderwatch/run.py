"""Stand-in wrapper: fetch the OCDS archive, run the SDK, email Ray, save state.

Usage:
  python -m tenderwatch.run new        # email new matching tenders
  python -m tenderwatch.run remind     # email deadline reminders for tenders already sent
Add --dry-run to print the email instead of sending it (no SMTP needed).
Add --demo to use demo/sample_releases.jsonl instead of downloading.
"""
from __future__ import annotations

import argparse
import gzip
import io
import json
import os
import smtplib
import ssl
import sys
import urllib.request
from datetime import datetime, timezone
from email.message import EmailMessage

from . import core

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVE = "https://github.com/RokctAI/opportunities/releases/download/ocds-{year}/releases-{year}-{month:02d}.jsonl.gz"
STATE = os.path.join(ROOT, "state", "sent.json")


def _months_back(now: datetime, n: int):
    y, m = now.year, now.month
    for _ in range(n):
        yield y, m
        y, m = (y, m - 1) if m > 1 else (y - 1, 12)


def fetch_releases(now: datetime, months: int):
    """Yield releases from the last `months` monthly shards of the opportunities OCDS archive."""
    for y, m in _months_back(now, months):
        url = ARCHIVE.format(year=y, month=m)
        try:
            with urllib.request.urlopen(url, timeout=120) as resp:
                data = resp.read()
        except Exception as exc:  # a missing month is not fatal
            print(f"skip {url}: {exc}", file=sys.stderr)
            continue
        for line in gzip.open(io.BytesIO(data), "rt", encoding="utf-8"):
            if line.strip():
                yield json.loads(line)


def demo_releases():
    with open(os.path.join(ROOT, "demo", "sample_releases.jsonl")) as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def render(mode: str, tenders: list[dict]) -> tuple[str, str]:
    if mode == "new":
        subject = f"{len(tenders)} new tender(s) matching your filters"
        intro = "New tenders that match your filters:"
    else:
        subject = f"{len(tenders)} tender deadline(s) coming up"
        intro = "Tenders I sent you before that close soon:"
    lines = [intro, ""]
    for t in tenders:
        closes = t["closes"][:16].replace("T", " ")
        lines += [
            f"- {t['number']}: {t['description']}",
            f"  {t['buyer']} ({t['province']}). Closes {closes} UTC",
            f"  {t['link']}",
            "",
        ]
    lines.append("Change what you receive by editing filters.json in the tenderwatch repo.")
    return subject, "\n".join(lines)


def send(subject: str, body: str) -> None:
    server = os.environ["SMTP_SERVER"]
    port = int(os.environ.get("SMTP_PORT") or 587)
    user = os.environ["SMTP_USERNAME"]
    to = os.environ.get("TENDER_EMAIL_TO") or user
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = user, to, subject
    msg.set_content(body)
    ctx = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(server, port, context=ctx) as s:
            s.login(user, os.environ["SMTP_PASSWORD"])
            s.send_message(msg)
    else:
        with smtplib.SMTP(server, port) as s:
            if (os.environ.get("SMTP_USE_TLS") or "true").lower() not in ("0", "false", "no"):
                s.starttls(context=ctx)
            s.login(user, os.environ["SMTP_PASSWORD"])
            s.send_message(msg)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["new", "remind"])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--filters", default=os.path.join(ROOT, "filters.json"))
    args = ap.parse_args(argv)

    now = datetime.now(timezone.utc)
    flt = core.load_filters(args.filters)
    sent = json.load(open(STATE)) if os.path.exists(STATE) else {}

    if args.mode == "new":
        releases = demo_releases() if args.demo else fetch_releases(now, flt.get("months_to_scan", 2))
        tenders = core.new_tenders(releases, flt, sent, now)
    else:
        tenders = core.due_reminders(sent, flt, now)

    if not tenders:
        print(f"{args.mode}: nothing to send")
        return 0
    subject, body = render(args.mode, tenders)
    if args.dry_run:
        print(subject, body, sep="\n\n")
        return 0
    send(subject, body)
    if args.mode == "new":
        with open(STATE, "w") as f:
            json.dump(core.record_sent(sent, tenders, now), f, indent=1, sort_keys=True)
    print(f"{args.mode}: emailed {len(tenders)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
