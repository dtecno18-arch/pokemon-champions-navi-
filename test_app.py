from pathlib import Path
import os, shutil, threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
CASES = [
    ['カバルドン','アシレーヌ','サーフゴー','ガブリアス','メガボーマンダ','ミミッキュ'],
    ['アーマーガア','ドヒドイデ','ラッキー','カバルドン','サーフゴー','ウルガモス'],
    ['イエッサン','メガルカリオZ','アシレーヌ','ゴリランダー','ブリジュラス','ガオガエン'],
]

def main():
    server=ThreadingHTTPServer(('127.0.0.1',0), partial(SimpleHTTPRequestHandler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    url=f'http://127.0.0.1:{server.server_port}/index.html'
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=os.environ.get("CHROMIUM_PATH") or (shutil.which("chromium") if not os.environ.get("CI") else None))
        for width in (390, 1280):
            page = browser.new_page(viewport={'width':width,'height':850})
            errors=[]
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.goto(url, wait_until='domcontentloaded')
            assert page.locator('#analyze').count()==1

            # The official M-C delta must be complete, including four Squawkabilly
            # feather forms. Do not confuse the 35 additions with all 352 forms.
            assert page.evaluate("() => officialMcAdditions.length") == 35
            assert page.evaluate("""() => officialMcAdditions.every(
                name => Array.from(document.querySelectorAll('#dex option'),
                    option => option.value).includes(name))""")
            for form in ('イキリンコ(グリーンフェザー)', 'イキリンコ(ブルーフェザー)',
                         'イキリンコ(イエローフェザー)', 'イキリンコ(ホワイトフェザー)'):
                assert page.locator('#dex option').evaluate_all(
                    "(els, form) => els.some(el => el.value === form)", form
                ), f'Missing M-C form: {form}'
            assert page.evaluate("""() => new Set(officialMcAdditions.filter(
                name => name.startsWith('イキリンコ')).map(formKey)).size""") == 4
            assert 'M-C追加35形態' in page.locator('#count + p').inner_text()
            assert '全352形態の網羅は未検証' in page.locator('#count + p').inner_text()
            assert 'raw.githubusercontent.com/fanzeyi/pokemon.json' not in page.content(), (
                'Unverified national Pokédex must not populate eligible suggestions'
            )
            # Newly added autocomplete entries are NOT automatically verified
            # matchup rules. Unknown threats must remain visibly unknown.
            unverified_mc = ['プクリン', 'マルノーム', 'オトスパス',
                             'ニャイキング', 'ネギガナイト', 'バチンウニ']
            for i, name in enumerate(unverified_mc):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#analyze').click()
            assert '0/6匹' in page.locator('#result .risk-banner').inner_text()
            assert page.locator('#result .abstention-banner').count() == 1, 'No verified matchup: must abstain'
            assert page.locator('#result .hero').count() == 0, 'Must not invent a default trio for six unknown opponents'
            assert all(name in page.locator('#result').inner_text() for name in unverified_mc)
            # Even sourced Mega facts are not a validated answer to the six
            # individual matchups; preserve Mega uncertainty while abstaining.
            unknown_mega = ['メガグソクムシャ','メガセグレイブ','メガガブリアスZ',
                            'ルカリオ','ゲッコウガ','メガジュペッタ']
            for i, name in enumerate(unknown_mega):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#analyze').click()
            assert page.locator('#result .hero').count() == 0
            assert page.locator('#result .abstention-banner').count() == 1
            assert page.locator('#result .sourced-intel').count() == 1
            assert '1/6匹' in page.locator('#result .evidence-summary').inner_text()
            mega_warning = page.locator('#result .mega-uncertainty').inner_text()
            assert all(name in mega_warning for name in unknown_mega), mega_warning
            # One named matchup answer among five unknown threats is not enough.
            one_answer = ['アシレーヌ','ガブリアス','ゲンガー',
                          'エースバーン','ドラパルト','ゲッコウガ']
            for i, name in enumerate(one_answer):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#analyze').click()
            assert page.locator('#result .abstention-banner').count() == 1
            assert page.locator('#result .hero').count() == 0
            assert '1/6匹' in page.locator('#result .abstention-banner').inner_text()
            assert '対策候補付きルール 1/6匹' in page.locator('#result .evidence-summary').inner_text()
            assert all(name in page.locator('#result').inner_text() for name in one_answer)
            # Indeedee is registered, but its rule has no answer.
            no_answer = ['イエッサン','ガブリアス','ゲンガー',
                         'エースバーン','ドラパルト','ゲッコウガ']
            for i, name in enumerate(no_answer):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#analyze').click()
            assert '1/6匹' in page.locator('#result .risk-banner').inner_text()
            assert '0/6匹' in page.locator('#result .abstention-banner').inner_text()
            assert page.locator('#result .hero').count() == 0
            # Two independent answers still produce a clearly provisional pick.
            two_answers = ['ゴリランダー','ドドゲザン','ガブリアス',
                           'ゲンガー','エースバーン','ドラパルト']
            for i, name in enumerate(two_answers):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#analyze').click()
            assert page.locator('#result .hero .chip').count() == 3
            assert '2/6匹' in page.locator('#result .evidence-summary').inner_text()
            assert '暫定' in page.locator('#result .hero').inner_text()
            # Regression: two registered opponent rules do not imply that the
            # actually chosen trio answers two threats. Prima + Hippo has
            # separate answers; the article-based trio only includes Mimikyu.
            partial_coverage = ['アシレーヌ','カバルドン','ガブリアス',
                                'ゲンガー','エースバーン','ドラパルト']
            assert page.evaluate('(names) => recommend(names).comparisonSummary.total', partial_coverage) == 2
            assert page.evaluate('(names) => recommend(names).comparisonSummary.chosen', partial_coverage) == 1
            for i, name in enumerate(partial_coverage):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#analyze').click()
            assert page.locator('#result .abstention-banner').count() == 1
            assert page.locator('#result .hero').count() == 0, 'One actual answer must not be a recommendation'
            assert '対策候補付きルール 2/6匹' in page.locator('#result .evidence-summary').inner_text()
            assert '選出3匹の対応 1/6匹' in page.locator('#result .evidence-summary').inner_text()
            assert all(name in page.locator('#result').inner_text() for name in partial_coverage)
            # Two actual answers remain eligible for a provisional suggestion.
            for i, name in enumerate(two_answers):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#analyze').click()
            assert page.locator('#result .hero .chip').count() == 3
            assert '選出3匹の対応 2/6匹' in page.locator('#result .evidence-summary').inner_text()
            for names in CASES:
                for i,name in enumerate(names):
                    page.locator(f'#foe{i}').fill(name)
                page.locator('#analyze').click()
                assert page.locator('#result').is_visible(), f'No result: {names}'
                assert len(page.locator('#result .hero .chip').all())==3, 'Must select 3'
                assert '先発' in page.locator('#result').inner_text()
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2'), 'Horizontal overflow'

            # A recommendation must use only the six configured team members.
            roster = {'カバルドン','メガルカリオZ','メガカイリュー','ミミッキュ','ギルガルド','イダイトウ♂'}
            for names in CASES:
                for i, name in enumerate(names):
                    page.locator(f'#foe{i}').fill(name)
                page.locator('#analyze').click()
                chosen = page.locator('#result .hero .chip').all_inner_texts()
                assert len(chosen) == 3 and len(set(chosen)) == 3, f'Duplicate or missing picks: {chosen}'
                assert all(name.strip() in roster for name in chosen), f'Outside configured roster: {chosen}'
                result_text = page.locator('#result').inner_text()
                assert all(name in result_text for name in names), 'Opponent coverage must mention all six inputs'
            # Lead safety regression: do not recommend Hippowdon into obvious
            # Rillaboom / Pelipper lead pressure when a fallback is selected.
            for danger in ('ゴリランダー', 'ペリッパー'):
                names = [danger,'ガブリアス','ゲンガー','エースバーン','ドドゲザン','ドラパルト']
                for i, name in enumerate(names):
                    page.locator(f'#foe{i}').fill(name)
                page.locator('#analyze').click()
                chips = [x.strip() for x in page.locator('#result .hero .chip').all_inner_texts()]
                result = page.locator('#result .hero').inner_text()
                lead = page.evaluate('(names) => recommend(names).lead', names)
                assert lead in chips, f'Lead must be one of the selected trio: {lead}, {chips}'
                assert lead != 'カバルドン', f'Unsafe Hippowdon lead vs {danger}: {chips}'
                assert '先発変更' in page.locator('#result').inner_text(), f'Missing safety explanation vs {danger}'
            # Without those specific dangers, preserve the article's baseline lead.
            safe_names = ['ガブリアス','ゲンガー','エースバーン','ドラパルト','ルカリオ','サザンドラ']
            assert page.evaluate('(names) => recommend(names).lead', safe_names) == 'カバルドン'

            # Data coverage must be obvious immediately below the recommendation.
            known_names = ['ミミッキュ','ドドゲザン','ペリッパー','ヤミラミ','ジュペッタ','アシレーヌ']
            for i, name in enumerate(known_names):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#analyze').click()
            banner = page.locator('#result .risk-banner')
            assert banner.count() == 1 and '6/6匹' in banner.inner_text(), banner.inner_text()
            assert banner.evaluate("(el) => el.previousElementSibling.classList.contains('hero')"), 'Coverage warning must be next to selection'

            unknown_names = ['ガブリアス','ウルガモス','ドラパルト','キラフロル','エースバーン','ゲッコウガ']
            for i, name in enumerate(unknown_names):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#analyze').click()
            banner = page.locator('#result .risk-banner')
            assert '0/6匹' in banner.inner_text(), banner.inner_text()
            assert all(name in banner.inner_text() for name in unknown_names), 'Missing unknown names in risk banner'
            assert '暫定案' in banner.inner_text(), 'Must not present unknown coverage as validated'
            assert page.locator('#result .abstention-banner').count() == 1
            assert page.locator('#result .hero').count() == 0, 'All-unknown opponents must not receive a recommended lead'
            assert all(name in page.locator('#result').inner_text() for name in unknown_names)

            # Opponent input survives reload, and explicit clear survives another reload.
            page.reload(wait_until='domcontentloaded')
            assert [page.locator(f'#foe{i}').input_value() for i in range(6)] == unknown_names
            page.locator('#analyze').click()
            assert '0/6匹' in page.locator('#result .risk-banner').inner_text()
            assert page.locator('#result .hero').count() == 0
            page.locator('#clear').click()
            page.reload(wait_until='domcontentloaded')
            assert all(page.locator(f'#foe{i}').input_value() == '' for i in range(6))

            # Mega safety: normal-form names can be Mega-capable; never assume
            # which of multiple possible Mega evolutions the opponent will use.
            mega_base_names = ['ボーマンダ','ルカリオ','ガブリアス','サーフゴー','ドドゲザン','ペリッパー']
            for i, name in enumerate(mega_base_names):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#analyze').click()
            mega_warning = page.locator('#result .mega-uncertainty')
            assert mega_warning.count() == 1, 'Base-form Mega candidates must trigger a warning'
            warning_text = mega_warning.inner_text()
            assert all(n in warning_text for n in mega_base_names[:3]), warning_text
            assert '確定できません' in warning_text, 'Must not guess the Mega user'
            assert 'サーフゴー' not in warning_text, 'Non-Mega candidate misidentified'

            explicit_mega = ['メガグソクムシャ','メガセグレイブ','サーフゴー','ドドゲザン','ペリッパー','イエッサン']
            for i, name in enumerate(explicit_mega):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#analyze').click()
            warning_text = page.locator('#result .mega-uncertainty').inner_text()
            assert all(n in warning_text for n in explicit_mega[:2]), warning_text

            no_mega = ['サーフゴー','ドドゲザン','ペリッパー','イエッサン','アシレーヌ','カバルドン']
            for i, name in enumerate(no_mega):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#analyze').click()
            assert page.locator('#result .mega-uncertainty').count() == 0

            # Form identity must not collapse Mega variants, sex or named forms
            # into a generic matchup rule. Species grouping is a separate concern.
            assert page.evaluate("() => formKey('メガリザードンX') !== formKey('メガリザードンY')")
            assert page.evaluate("() => formKey('イダイトウ♂') !== formKey('イダイトウ♀')")
            assert page.evaluate("() => formKey('ストリンダー(ハイ)') !== formKey('ストリンダー(ロー)')")
            assert page.evaluate("() => formKey('メガルカリオZ') !== formKey('ルカリオ')")
            assert page.evaluate("() => normalize('メガリザードンX') === normalize('メガリザードンY')")
            for form in ('メガアブソルZ', 'メガガブリアスZ', 'メガグソクムシャ',
                         'メガセグレイブ', 'ストリンダー(ハイ)', 'ストリンダー(ロー)',
                         'イエッサン(オス)', 'イエッサン(メス)',
                         'メガリザードンX', 'メガリザードンY'):
                assert page.locator('#dex option').evaluate_all(
                    "(els, form) => els.some(el => el.value === form)", form
                ), f'Missing form autocomplete: {form}'

            # A rule for base-form Banette must NOT silently validate Mega Banette.
            form_case = ['メガジュペッタ', 'ミミッキュ', 'ドドゲザン',
                         'ペリッパー', 'ヤミラミ', 'アシレーヌ']
            for i, name in enumerate(form_case):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#analyze').click()
            form_banner = page.locator('#result .risk-banner').inner_text()
            assert '5/6匹' in form_banner and 'メガジュペッタ' in form_banner, form_banner
            assert page.evaluate("(names) => recommend(names).coverage[0].status", form_case) == '要確認'
            assert 'M-C全352種類の入力候補網羅：未検証' in page.locator('#result').inner_text()

            # Normal Lucario is not proof that Mega Lucario Z is selected.
            base_lucario = ['ルカリオ', 'アシレーヌ', 'サーフゴー',
                            'ドドゲザン', 'ミミッキュ', 'ペリッパー']
            z_lucario = ['メガルカリオZ', *base_lucario[1:]]
            base_reason = page.evaluate("(names) => recommend(names).reason", base_lucario)
            z_reason = page.evaluate("(names) => recommend(names).reason", z_lucario)
            assert '相手のルカリオZとアシレーヌ' not in base_reason, base_reason
            assert '相手のルカリオZとアシレーヌ' in z_reason, z_reason

            # Regression: Porygon-Z is a species name, not a Mega suffix.
            assert page.evaluate("() => normalize('ポリゴンZ') === 'ポリゴンZ'")
            assert page.evaluate("() => normalize('ポリゴンZ') !== normalize('ポリゴン')")
            assert page.evaluate("() => normalize('メガリザードンY') === 'リザードン'")

            # GameWith-sourced Mega Golisopod threat intelligence must be visible
            # without falsely promoting a provisional matchup into a safe verdict.
            goli_mega = ['メガグソクムシャ','サーフゴー','ガブリアス',
                         'ドドゲザン','ペリッパー','アシレーヌ']
            for i, name in enumerate(goli_mega):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#analyze').click()
            intel_card = page.locator('#result .sourced-intel')
            assert intel_card.count() == 1
            intel_text = intel_card.inner_text()
            for term in ('むし・はがね','かたいツメ','素早さ40','ふいうち',
                         'であいがしら','アクアジェット','2026-10-26','未検証'):
                assert term in intel_text, (term, intel_text)
            assert page.locator('#result .evidence-summary').count() == 1
            assert '1/6匹' in page.locator('#result .evidence-summary').inner_text()
            assert 'メガグソクムシャ' in page.locator('#result .risk-banner').inner_text()
            assert intel_card.locator('a[href="https://gamewith.jp/pokemon-champions/575652"]').count() == 1

            # A normal-form Golisopod is only a *possible* Mega.
            page.locator('#foe0').fill('グソクムシャ')
            page.locator('#analyze').click()
            assert 'メガシンカするかは未確定' in page.locator('#result .sourced-intel').inner_text()
            assert '0/6匹' in page.locator('#result .evidence-summary').inner_text()
            assert 'グソクムシャ' in page.locator('#result .risk-banner').inner_text()

            # Unrelated opponents must not inherit this form-specific profile.
            page.locator('#foe0').fill('エースバーン')
            page.locator('#analyze').click()
            assert page.locator('#result .sourced-intel').count() == 0

            # Unknown Pokémon must not crash the app or inject markup.
            # Refill all slots after the explicit clear/reload above.
            for i, name in enumerate(unknown_names):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#foe0').fill('<img src=x onerror=alert(1)>')
            page.locator('#analyze').click()
            assert page.locator('#result').is_visible()
            assert page.locator('#result img').count() == 0, 'User input injected an HTML image'
            assert not errors, errors
            page.locator('#clear').click()
            assert not page.locator('#result').is_visible()
            assert all(page.locator(f'#foe{i}').input_value()=='' for i in range(6))
            assert not errors, errors
            page.close()
        browser.close()
    server.shutdown()
    print('PASS: selection, lead, confidence banner, persistence, clear, overflow, runtime errors on mobile/desktop')

if __name__=='__main__': main()
