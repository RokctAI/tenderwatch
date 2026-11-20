# tenderwatch

Emails Ray South African government tenders that match his filters, twice a week.
A small stand-in until the tender SDK moves into the platform.

- **Tuesday 08:00 SAST**: new tenders that match `filters.json` and were never emailed before.
- **Friday 08:00 SAST**: reminders for tenders already emailed that close within 7 days.

No Claude thread or token spend is involved; it runs on GitHub Actions only.

## Where the tenders come from

The eTenders OCDS archive that the `opportunities` repo keeps fresh in its GitHub
Releases (synced Tue + Fri 02:00 UTC from the National Treasury eTenders API).
tenderwatch reads the last two monthly shards directly, so it does not depend on
`opportunities/published/api/tenders.json`, which stopped getting new tenders after
September 2026.

## Change what you receive

Edit `filters.json` on GitHub. An empty list means "no limit".

| Key | Meaning |
|---|---|
| `keywords_any` | Tender must mention at least one of these (tender number, description, planning note) |
| `keywords_exclude` | Drop a tender that mentions any of these |
| `categories` | `goods`, `services`, `works` |
| `provinces` | Matched from the buyer name, e.g. `Gauteng`, `Limpopo`; others are `National` |
| `buyers_any` / `buyers_exclude` | Part of a buyer name to keep or drop |
| `min_days_left` | Skip tenders closing sooner than this |
| `remind_within_days` | Friday reminder window |
| `months_to_scan` | How many monthly archive shards to read |
| `max_per_email` | Cap per email |

## Setup (once)

The SMTP settings are not stored here. Each run reads `SMTP_SERVER`, `SMTP_PORT`,
`SMTP_USERNAME`, `SMTP_PASSWORD` and `SMTP_USE_TLS` (and optional `TENDER_EMAIL_TO`,
otherwise mail goes to `SMTP_USERNAME`) from RokctAI/Occultation `.env/production.env`
using the `MONOREPO_PAT` org secret, the same way `play-deploy` reads package names.
Values are masked in the logs.

1. Make sure `MONOREPO_PAT` is available to this repo.
2. Actions > tenderwatch > Run workflow with `dry_run` ticked to see the email in the log;
   untick it to send for real.

## Layout

- `tenderwatch/core.py`: the SDK. Pure logic (normalise, filter, new vs sent, reminders).
  No network or email, so it can move into the platform as is.
- `tenderwatch/run.py`: the stand-in wrapper (download archive, send SMTP, save state).
- `state/sent.json`: tenders already emailed, committed back by the workflow.
- `demo/sample_releases.jsonl`: demo data. Try `python -m tenderwatch.run new --demo --dry-run`.

This is a backend job, not an app-facing SDK, so it has no tour; this README is the guide.

Spawned by [RokctAI Factory](https://github.com/rokctai/factory) from <https://github.com/RokctAI/factory/issues/72>. Brief: [docs/spec.md](docs/spec.md).
