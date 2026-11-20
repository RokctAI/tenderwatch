# tenderwatch — accepted brief

> Copied verbatim from https://github.com/RokctAI/factory/issues/72 at spawn time. Do not edit: this is the
> record of what was accepted. Decisions taken while building belong in
> `.rokct/decision_log.md`.

**One line:** Emails Ray filtered SA government tenders twice a week (new tenders Tue, deadline reminders Fri)

## Rationale

Stand-in for the tender SDK until it moves into the platform, so the tender scouting thread can retire and stop spending tokens.

It reads the eTenders OCDS archive that RokctAI/opportunities keeps in its GitHub Releases (synced Tue + Fri 02:00 UTC), filters it with an editable `filters.json` (keywords, exclusions, category, province, buyer, days left), and emails Ray over SMTP using the org SMTP secrets. Tuesday 08:00 SAST: new matching tenders not emailed before. Friday 08:00 SAST: reminders for already-emailed tenders closing within 7 days. A `state/sent.json` ledger is committed back by the workflow.

Pure SDK logic (`tenderwatch/core.py`, stdlib only) is kept separate from the schedule/email wrapper (`tenderwatch/run.py`) so the SDK can move into the platform unchanged. Backend job, no app UI, no tour; README is the guide; demo data included.

Public because private repos have no Actions minutes; it holds only public tender data and filter words. Code is ready and will be pushed as a draft PR once the repo exists.

Done = Ray receives the first real Tuesday email, then retires the tender thread.
