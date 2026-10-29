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
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

OFFICIAL_URL = "https://web-view.app.pokemonchampions.jp/battle/pages/events/rs178713870219xeaaio/ja/pokemon.html"
ALTERNATE_URL = "https://web-view.app.pokemonchampions.jp/battle/pages/events/ic178714032620uzyrlm/ja/pokemon.html"
REPORT = Path(os.environ.get("MC_AUDIT_REPORT", "mc-roster-audit.json"))
APP = Path(os.environ.get("MC_AUDIT_APP", "index.html"))
MIN_EXPECTED = 262  # Official M-C has 262 battle-form entries (2026-10-29).
# Independent, live Mega notices. Count-only checks can miss a swapped form.
MEGA_NOTICES = {
    "M-A": ("https://champions-news.pokemon-home.com/ja/page/751.html", 59),
    "M-B": ("https://champions-news.pokemon-home.com/ja/page/776.html", 16),
    "M-C": ("https://news.pokemon-home.com/ja/page/816.html", 6),
}
MEGA_SEX_EXPANSIONS = {"メガニャオニクス": ["メガニャオニクス(オス)", "メガニャオニクス(メス)"]}


# Official eligible-list codes collapse some cosmetic forms to one battle entry.
# Expand only with independently dated form-specific evidence.
FORM_EXPANSIONS = {
    "0670-005": ["フラエッテ(えいえんのはな)"],
    "0925-001": ["イッカネズミ(3びき)", "イッカネズミ(4ひき)"],
    "0931-000": ["イキリンコ(グリーンフェザー)", "イキリンコ(ブルーフェザー)"],
    "0931-002": ["イキリンコ(イエローフェザー)", "イキリンコ(ホワイトフェザー)"],
    "1013-000": ["ヤバソチャ(ボンサクのすがた)", "ヤバソチャ(ケッサクのすがた)"],
}
EXPANSION_SOURCES = {
    "0670-005": ("https://gamewith.jp/pokemon-champions/553326", "2026-10-27", "secondary source; official form code 005"),
    "0925-001": ("https://champions-news.pokemon-home.com/en/page/834.html", "2026-09-18", "official M-C special roster"),
    "0931-000": ("https://champions-news.pokemon-home.com/ja/page/821.html", "2026-09-09", "official M-C select, same battle-ability group"),
    "0931-002": ("https://champions-news.pokemon-home.com/ja/page/821.html", "2026-09-09", "official M-C select, same battle-ability group"),
    "1013-000": ("https://champions-news.pokemon-home.com/en/page/834.html", "2026-09-18", "official M-C special roster"),
}


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


def extract_official_megas(text):
    """Read only the Mega list between the official notice and item headings.

    Normalize full-width X/Y/Z and reject a missing section instead of
    accepting an unrelated article paragraph containing 'メガ'.
    """
    text = unicodedata.normalize("NFKC", text).replace("\u200b", "")
    start = "下記のポケモンです。"
    end = "ポケモンの持ち物"
    if start not in text or end not in text.split(start, 1)[1]:
        raise ValueError("Official Mega notice section missing")
    section = text.split(start, 1)[1].split(end, 1)[0]
    names = re.findall(r"メガ[ァ-ヶー]+(?:[XYZ])?", section)
    if not names or len(names) != len(set(names)):
        raise ValueError("Official Mega notice empty or duplicated")
    return names


def reconcile_official_megas(notices, app_buckets, app_inputs, candidates):
    """Exact set equality, not merely 82 Megas by count."""
    for regulation, (url, expected_count) in MEGA_NOTICES.items():
        source = notices.get(regulation, [])
        app = app_buckets.get(regulation, [])
        if len(source) != expected_count or len(app) != expected_count:
            raise ValueError(f"{regulation} Mega count changed: official={len(source)}, app={len(app)}")
        if len(set(app)) != len(app):
            raise ValueError(f"{regulation} app Mega list has duplicate entries")
    official = {key: set(names) for key, names in notices.items()}
    app = {key: set(names) for key, names in app_buckets.items()}
    bucket_diff = {key: {
        "missing": sorted(official[key] - app[key]),
        "extra": sorted(app[key] - official[key]),
    } for key in MEGA_NOTICES}
    named = set().union(*official.values())
    if sum(map(len, official.values())) != len(named):
        raise ValueError("Same official Mega appears in multiple regulations")
    expanded = set(named)
    for base, forms in MEGA_SEX_EXPANSIONS.items():
        if base not in expanded:
            raise ValueError(f"Missing source for Mega sex expansion: {base}")
        expanded.remove(base)
        expanded.update(forms)
    inputs = set(app_inputs)
    actual = set(candidates)
    return {
        "officialNamed": len(named),
        "officialExpanded": len(expanded),
        "bucketDiff": bucket_diff,
        "inputMissing": sorted(expanded - inputs),
        "inputExtra": sorted(inputs - expanded),
        "candidateMissing": sorted(expanded - actual),
        "candidateExtra": sorted(actual - expanded),
        "duplicateInputs": len(app_inputs) != len(inputs),
        "duplicateCandidates": len(candidates) != len(actual),
        "passed": all(not d["missing"] and not d["extra"] for d in bucket_diff.values())
            and len(named) == 81 and len(expanded) == 82
            and inputs == expanded and actual == expanded
            and len(app_inputs) == len(inputs) and len(candidates) == len(actual),
    }


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
        # Fail closed if the official embedded form IDs disappear or a
        # documented cosmetic expansion is no longer backed by this roster.
        codes = {entry[2] for entry in entries if len(entry) == 3}
        if len(codes) != len(entries) or not set(FORM_EXPANSIONS).issubset(codes):
            raise RuntimeError("Official form IDs incomplete or changed; do not certify")
        if set(FORM_EXPANSIONS) != set(EXPANSION_SOURCES):
            raise RuntimeError("Cosmetic expansion missing a dated source")
        expanded = [(dex, name, code, FORM_EXPANSIONS.get(code, [name]))
                    for dex, name, code in entries]
        mega_notices = {}
        mega_sources = []
        for regulation, (url, expected) in MEGA_NOTICES.items():
            notice = browser.new_page(locale="ja-JP")
            try:
                response = notice.goto(url, wait_until="domcontentloaded", timeout=30000)
                if response is None or response.status != 200:
                    raise RuntimeError(f"{regulation} official Mega notice HTTP error")
                names = extract_official_megas(notice.locator("body").inner_text(timeout=15000))
                if len(names) != expected:
                    raise RuntimeError(f"{regulation} official Mega notice changed: {len(names)} != {expected}")
                mega_notices[regulation] = names
                mega_sources.append({"regulation": regulation, "url": url,
                                     "count": len(names), "httpStatus": response.status})
            finally:
                notice.close()
        app = browser.new_page(locale="ja-JP")
        app.goto(APP.resolve().as_uri(), wait_until="load")
        data = app.evaluate("""(official) => {
            const options = Array.from(document.querySelectorAll('#dex option'), o => o.value);
            const normal = options.filter(n => !isMegaForm(n));
            return {
                inputCount: options.length,
                nonMegaCount: normal.length,
                megaCount: options.filter(isMegaForm).length,
                official: official.map(([dex, name, code, forms]) => ({dex, name, code, keys: forms.map(formKey)})),
                candidates: normal.map(name => ({name, key: formKey(name)})),
                megaBuckets: {'M-A': officialMegaMa, 'M-B': officialMegaMb, 'M-C': officialMegaMc},
                megaInputForms: megaInputForms.map(formKey),
                // Independent prefix check catches unknown Mega entries even if
                // isMegaForm() fails to recognize them.
                actualMegaCandidates: options.filter(n => n.startsWith('メガ')).map(formKey)
            };
        }""", expanded)
        browser.close()
    mega_audit = reconcile_official_megas(
        mega_notices, data["megaBuckets"], data["megaInputForms"], data["actualMegaCandidates"]
    )
    official_keys = {key for x in data["official"] for key in x["keys"]}
    official_labels = [(x["dex"], x["name"]) for x in data["official"]]
    ambiguous = [x for x in data["official"]
                 if official_labels.count((x["dex"], x["name"])) > 1]
    unresolved_ambiguities = [x for x in ambiguous if x["code"] not in FORM_EXPANSIONS]
    candidate_keys = {x["key"] for x in data["candidates"]}
    missing = [{**x, "missingKey": key} for x in data["official"]
               for key in x["keys"] if key not in candidate_keys]
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
        "unresolvedAmbiguities": unresolved_ambiguities,
        "documentedFormExpansions": [{"code": code, "forms": forms, "source": EXPANSION_SOURCES[code][0], "updated": EXPANSION_SOURCES[code][1], "basis": EXPANSION_SOURCES[code][2]} for code, forms in FORM_EXPANSIONS.items()],
        "megaInputForms": data["megaCount"],
        "megaNoticeSources": mega_sources,
        "megaExactAudit": mega_audit,
        "passed": not missing and not extra and not duplicate_keys and not unresolved_ambiguities and len(official_keys) == data["nonMegaCount"] and len(entries) >= MIN_EXPECTED and data["megaCount"] == 82 and mega_audit["passed"],
        "scope": "262 official M-C battle-form codes plus documented cosmetic expansions; all 81 official Mega names (82 input forms) checked by exact set equality against live M-A/B/C notices."
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
