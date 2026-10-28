#!/usr/bin/env python3
"""Fail-closed M-C roster audit using the official eligibility page.

Usage: python tools/audit_official_mc.py
Requires: playwright and Chromium. Writes mc-roster-audit.json even on error.
The 35 newly added forms alone are NOT a full M-C roster audit.
"""
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

OFFICIAL_URL = "https://web-view.app.pokemonchampions.jp/battle/pages/events/rs178713870219xeaaio/ja/pokemon.html"
REPORT = Path(os.environ.get("MC_AUDIT_REPORT", "mc-roster-audit.json"))
APP = Path(os.environ.get("MC_AUDIT_APP", "index.html"))
MIN_EXPECTED = 200


def extract_official(text):
    """Return (national Dex number, exact official Japanese form label)."""
    entries = []
    for line in text.splitlines():
        m = re.match(r"^\s*No\.?\s*(\d{3,4})\s+(.+?)\s*$", line, re.I)
        if m:
            entries.append((int(m.group(1)), m.group(2).strip()))
    return entries


def audit():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        official = browser.new_page(locale="ja-JP", viewport={"width": 1280, "height": 900})
        response = official.goto(OFFICIAL_URL, wait_until="domcontentloaded", timeout=45000)
        official.wait_for_timeout(12000)
        page_text = official.locator("body").inner_text(timeout=20000)
        entries = extract_official(page_text)
        if len(entries) < MIN_EXPECTED:
            raise RuntimeError(
                f"Official roster returned {len(entries)} entries (<{MIN_EXPECTED}); "
                f"HTTP {response.status if response else 'unknown'}, "
                f"body prefix: {page_text[:350]!r}. Coverage NOT certified."
            )
        if len(set(entries)) != len(entries):
            raise RuntimeError("Duplicate dex+form entries in official source")
        app = browser.new_page(locale="ja-JP")
        app.goto(APP.resolve().as_uri(), wait_until="load")
        data = app.evaluate("""(official) => {
            const options = Array.from(document.querySelectorAll('#dex option'), o => o.value);
            const normal = options.filter(n => !isMegaForm(n));
            return {
                inputCount: options.length,
                nonMegaCount: normal.length,
                official: official.map(([dex, name]) => ({dex, name, key: formKey(name)})),
                candidates: normal.map(name => ({name, key: formKey(name)}))
            };
        }""", entries)
        browser.close()
    official_keys = {x["key"] for x in data["official"]}
    candidate_keys = {x["key"] for x in data["candidates"]}
    missing = [x for x in data["official"] if x["key"] not in candidate_keys]
    extra = [x for x in data["candidates"] if x["key"] not in official_keys]
    keys = [x["key"] for x in data["candidates"]]
    duplicate_keys = sorted({k for k in keys if keys.count(k) > 1})
    return {
        "source": OFFICIAL_URL,
        "checkedAtUtc": datetime.now(timezone.utc).isoformat(),
        "officialEntries": len(entries),
        "officialUniqueForms": len(official_keys),
        "appInputCandidates": data["inputCount"],
        "appNonMegaCandidates": data["nonMegaCount"],
        "missing": missing,
        "extra": extra,
        "duplicateCandidateKeys": duplicate_keys,
        "passed": not missing and not extra and not duplicate_keys and len(official_keys) == len(entries),
        "scope": "Official M-C non-Mega eligibility only; Mega eligibility requires separate official audit."
    }


def main():
    try:
        result = audit()
    except Exception as exc:
        result = {
            "passed": False,
            "source": OFFICIAL_URL,
            "checkedAtUtc": datetime.now(timezone.utc).isoformat(),
            "error": str(exc),
            "scope": "No verified coverage: source extraction failed closed."
        }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
