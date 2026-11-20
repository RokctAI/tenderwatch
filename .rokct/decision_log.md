# Decision log

- 2026-11-20: Python stdlib only, no Flutter/Frappe stack. A stand-in until the tender SDK moves into the platform (Ray), so kept small.
- 2026-11-20: Source is the opportunities OCDS archive (GitHub Release assets), not `published/api/tenders.json`, which stopped getting new tenders after Sept 2026.
- 2026-11-20: SDK logic (`tenderwatch/core.py`) has no I/O so it can move into the platform unchanged; `run.py` is the wrapper.
- 2026-11-20: Public repo: private repos have no Actions minutes. Only public tender data and filter words live here; SMTP credentials are org secrets.
- 2026-11-20: Protocol bootstrap not run yet (keeps the stand-in small); run `bash .rokct/bootstrap.sh` if the repo needs protocol skills later.
- 2026-11-20: Backend job, not app-facing, so no tour; README is the guide; demo data in `demo/`.
