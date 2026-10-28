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
ALTERNATE_URL = "https://web-view.app.pokemonchampions.jp/battle/pages/events/ic178714032620uzyrlm/ja/pokemon.html"
REPORT = Path(os.environ.get("MC_AUDIT_REPORT", "mc-roster-audit.json"))
APP = Path(os.environ.get("MC_AUDIT_APP", "index.html"))
MIN_EXPECTED = 200


def extract_official(text):
    """Extract entries even when hidden DOM text has no newline separators.

    The official page currently keeps the full roster in hidden DOM nodes:
    body.inner_text() returns only its heading, while body.text_content()
    concatenates the individual No.XXXX entries. Split on each No. marker.
    """
    markers = list(re.finditer(r"No\.?\s*(\d{3,4})\s*", text, re.I))
    entries = []
    for i, marker in enumerate(markers):
        end = markers[i + 1].start() if i + 1 < len(markers) else len(text)
        raw_name = text[marker.end():end].split("©")[0]
        name = re.sub(r"\s+", " ", raw_name).strip()
        if name and len(name) < 100:
            entries.append((int(marker.group(1)), name))
    return entries
def extract_official_payload(text):
    """Parse the official page's embedded exact-form roster with form IDs.

    Source HTML contains: const pokemons = [["0003-000",1,"フシギバナ"], ...];
    Unlike rendered labels, the code distinguishes same-named forms.
    """
    match = re.search(r"const\s+pokemons\s*=\s*(\[\[.*?\]\])\s*;", text, re.S)
    if not match:
        return []
    rows = json.loads(match.group(1))
    if not isinstance(rows, list):
        raise ValueError("Official embedded roster is not an array")
    out = []
    for row in rows:
        if (not isinstance(row, list) or len(row) < 3 or
                not isinstance(row[0], str) or
                not re.fullmatch(r"\d{4}-\d{3}", row[0]) or
                not isinstance(row[2], str) or not row[2].strip()):
            raise ValueError(f"Malformed official form row: {row!r}")
        out.append((int(row[0][:4]), row[2].strip(), row[0]))
    if len({x[2] for x in out}) != len(out):
        raise ValueError("Duplicate official form IDs")
    return out


def audit():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        official = browser.new_page(locale="ja-JP", viewport={"width": 1280, "height": 900})
        network = []
        official.on("response", lambda response: network.append({"status": response.status, "url": response.url.split("?")[0]}))
        attempts = []
        for actual_source in (OFFICIAL_URL, ALTERNATE_URL):
            response = official.goto(actual_source, wait_until="domcontentloaded", timeout=45000)
            official.wait_for_timeout(10000)
            page_text = official.locator("body").inner_text(timeout=20000)
            raw_text = official.locator("body").text_content(timeout=20000) or ""
            entries = extract_official_payload(raw_text)
            if len(entries) < MIN_EXPECTED:
                entries = extract_official(page_text)
            if len(entries) < MIN_EXPECTED:
                entries = extract_official(raw_text)
            attempts.append({"url": actual_source, "entries": len(entries),
                             "rawTextLength": len(raw_text), "htmlLength": len(official.content()),
                             "htmlContainsDexNo": "No.0003" in official.content(),
                             "status": response.status if response else None,
                             "prefix": page_text[:160]})
            if len(entries) >= MIN_EXPECTED and {"プクリン", "セグレイブ"}.issubset(
                    {entry[1] for entry in entries}):
                break
        Path("mc-official-body.txt").write_text(page_text + "\n--- RAW TEXT CONTENT ---\\n" + raw_text, encoding="utf-8")
        Path("mc-official-network.json").write_text(json.dumps(network, ensure_ascii=False, indent=2), encoding="utf-8")
        official.screenshot(path="mc-official-snapshot.png", full_page=True)
        if len(entries) < MIN_EXPECTED or not {"プクリン", "セグレイブ"}.issubset(
                {entry[1] for entry in entries}):
            raise RuntimeError(f"No complete current M-C roster extracted; attempts={attempts!r}; network={network[-12:]!r}. Coverage NOT certified.")
        # Official text may omit visually distinguished variants (e.g. plumage).
        # Preserve ambiguous duplicates in the report and FAIL the quality gate.
        app = browser.new_page(locale="ja-JP")
        app.goto(APP.resolve().as_uri(), wait_until="load")
        data = app.evaluate("""(official) => {
            const options = Array.from(document.querySelectorAll('#dex option'), o => o.value);
            const normal = options.filter(n => !isMegaForm(n));
            return {
                inputCount: options.length,
                nonMegaCount: normal.length,
                official: official.map(([dex, name, code]) => ({dex, name, code: code || null, key: formKey(name)})),
                candidates: normal.map(name => ({name, key: formKey(name)}))
            };
        }""", entries)
        browser.close()
    official_keys = {x["key"] for x in data["official"]}
    official_labels = [(x["dex"], x["key"]) for x in data["official"]]
    ambiguous = [x for x in data["official"] if official_labels.count((x["dex"], x["key"])) > 1]
    candidate_keys = {x["key"] for x in data["candidates"]}
    missing = [x for x in data["official"] if x["key"] not in candidate_keys]
    extra = [x for x in data["candidates"] if x["key"] not in official_keys]
    keys = [x["key"] for x in data["candidates"]]
    duplicate_keys = sorted({k for k in keys if keys.count(k) > 1})
    return {
        "source": actual_source,
        "checkedAtUtc": datetime.now(timezone.utc).isoformat(),
        "officialEntries": len(entries),
        "officialFormCodes": len({x[2] for x in entries if len(x) > 2}),
        "formCodeSamples": [{"dex": x[0], "name": x[1], "code": x[2]} for x in entries if len(x) > 2 and x[0] in (479,670,711,876,902,925,931,1013)],
        "lastOfficialRawPreview": raw_text[raw_text.rfind("No.1019"):][:350],
        "officialUniqueForms": len(official_keys),
        "appInputCandidates": data["inputCount"],
        "appNonMegaCandidates": data["nonMegaCount"],
        "missing": missing,
        "extra": extra,
        "duplicateCandidateKeys": duplicate_keys,
        "ambiguousOfficialLabels": ambiguous,
        "passed": not missing and not extra and not duplicate_keys and not ambiguous and len(official_keys) == len(entries),
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
