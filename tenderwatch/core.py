"""Pure tender logic. No network, no email, no files beyond what callers pass in,
so this module can move into the platform later unchanged."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

PROVINCES = [
    "Eastern Cape", "Free State", "Gauteng", "KwaZulu-Natal", "Limpopo",
    "Mpumalanga", "North West", "Northern Cape", "Western Cape",
]
_PROVINCE_ALIASES = {"kwazulu natal": "KwaZulu-Natal", "kzn": "KwaZulu-Natal"}


def _parse_dt(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def _province(buyer: str) -> str:
    low = buyer.lower()
    for alias, name in _PROVINCE_ALIASES.items():
        if low.startswith(alias):
            return name
    for p in PROVINCES:
        if low.startswith(p.lower()):
            return p
    return "National"


def normalise(release: dict) -> dict | None:
    """One OCDS release -> a flat tender dict, or None if it has no closing date."""
    t = release.get("tender") or {}
    closes = _parse_dt((t.get("tenderPeriod") or {}).get("endDate"))
    if not closes:
        return None
    buyer = (release.get("buyer") or {}).get("name") or (t.get("procuringEntity") or {}).get("name") or ""
    plan = release.get("planning") or {}
    docs = t.get("documents") or []
    detail = " ".join(((plan.get("rationale") or "") + " " + ((plan.get("budget") or {}).get("description") or "")).split())
    return {
        "ocid": release.get("ocid"),
        "number": " ".join((t.get("title") or "").split()),
        "description": " ".join((t.get("description") or "").split()) or detail,
        "detail": detail,
        "category": t.get("mainProcurementCategory") or "",
        "method": t.get("procurementMethodDetails") or "",
        "buyer": buyer,
        "province": _province(buyer),
        "published": (t.get("tenderPeriod") or {}).get("startDate") or release.get("date"),
        "closes": closes.isoformat(),
        "documents": [d.get("url") for d in docs if d.get("url")],
        # First tender document on eTenders; the OCDS data carries no public page URL.
        "link": next((d.get("url") for d in docs if d.get("url")), "https://www.etenders.gov.za/Home/opportunities"),
    }


def load_filters(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def _text(t: dict) -> str:
    return " ".join([t["number"], t["description"], t["detail"]]).lower()


def matches(t: dict, flt: dict, now: datetime) -> bool:
    """True if the tender passes every filter that is set. Empty list = no limit."""
    closes = _parse_dt(t["closes"])
    if closes is None or closes < now + timedelta(days=flt.get("min_days_left", 0)):
        return False
    text = _text(t)
    if flt.get("keywords_any") and not any(k.lower() in text for k in flt["keywords_any"]):
        return False
    if any(k.lower() in text for k in flt.get("keywords_exclude", [])):
        return False
    if flt.get("categories") and t["category"] not in flt["categories"]:
        return False
    if flt.get("provinces") and t["province"] not in flt["provinces"]:
        return False
    if flt.get("buyers_any") and not any(b.lower() in t["buyer"].lower() for b in flt["buyers_any"]):
        return False
    if any(b.lower() in t["buyer"].lower() for b in flt.get("buyers_exclude", [])):
        return False
    return True


def new_tenders(releases, flt: dict, sent: dict, now: datetime | None = None) -> list[dict]:
    """Open tenders that match the filters and were never emailed before, soonest closing first."""
    now = now or datetime.now(timezone.utc)
    seen, out = set(), []
    for r in releases:
        t = normalise(r)
        if not t or t["ocid"] in sent or t["ocid"] in seen:
            continue
        if matches(t, flt, now):
            seen.add(t["ocid"])
            out.append(t)
    out.sort(key=lambda t: t["closes"])
    return out[: flt.get("max_per_email", 50)]


def due_reminders(sent: dict, flt: dict, now: datetime | None = None) -> list[dict]:
    """Tenders already emailed that close within remind_within_days and have not closed."""
    now = now or datetime.now(timezone.utc)
    horizon = now + timedelta(days=flt.get("remind_within_days", 7))
    out = [t for t in sent.values() if now < _parse_dt(t["closes"]) <= horizon]
    return sorted(out, key=lambda t: t["closes"])


def record_sent(sent: dict, tenders: list[dict], now: datetime | None = None) -> dict:
    """Add emailed tenders to the sent ledger and drop ones that closed over 30 days ago."""
    now = now or datetime.now(timezone.utc)
    for t in tenders:
        sent[t["ocid"]] = {k: t[k] for k in ("ocid", "number", "description", "buyer", "province", "closes", "link")}
        sent[t["ocid"]]["sent_at"] = now.isoformat()
    cutoff = now - timedelta(days=30)
    return {k: v for k, v in sent.items() if _parse_dt(v["closes"]) > cutoff}
