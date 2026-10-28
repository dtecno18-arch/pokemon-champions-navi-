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

            # Official 2026 M-A Global Challenge roster: 31 distinct forms,
            # including region, sex and family-size variants (historical
            # eligibility only; M-C audit remains incomplete).
            assert page.evaluate("() => officialMaSpecialRoster.length") == 31
            assert page.evaluate("""() => officialMaSpecialRoster.every(
                name => Array.from(document.querySelectorAll('#dex option'),
                    option => option.value).includes(name))""")
            assert page.evaluate("() => document.querySelectorAll('#dex option').length") == 245
            assert '公式M-A特別セレクト31形態' in page.locator('#count + p').inner_text()
            assert '全352形態の網羅は未検証' in page.locator('#count + p').inner_text()
            ma_new = ['アローラキュウコン','コータス','エルフーン',
                      'ニャオニクス(メス)','イダイトウ(オス)','イッカネズミ(3びき)']
            for i, name in enumerate(ma_new):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#analyze').click()
            assert page.locator('#result .candidate-unverified').count() == 0
            assert page.locator('#result .abstention-banner').count() == 1
            assert page.locator('#result .hero').count() == 0
            assert '検証済み対面 0/6匹' in page.locator('#result .evidence-summary').inner_text()

            # Form-aware lookup must remain distinct from species-level
            # duplicate detection. A regional or appliance form cannot
            # occupy a second preview slot of the same species.
            assert page.evaluate("() => normalize('ペルシアン') === normalize('アローラペルシアン')")
            assert page.evaluate("() => normalize('キュウコン') === normalize('アローラキュウコン')")
            assert page.evaluate("() => normalize('ウォッシュロトム') === normalize('ヒートロトム')")
            assert page.evaluate("() => formKey('ペルシアン') !== formKey('アローラペルシアン')")
            assert page.evaluate("() => formKey('ウォッシュロトム') !== formKey('ヒートロトム')")
            assert page.evaluate("() => formKey('ペルシアン（アローラのすがた）') === formKey('アローラペルシアン')")
            assert page.evaluate("() => formKey('イダイトウ♂') === formKey('イダイトウ(オス)')")
            assert page.evaluate("() => formKey('イダイトウ(オス)') !== formKey('イダイトウ(メス)')")
            for first, second in (
                ('ペルシアン','アローラペルシアン'),
                ('キュウコン','アローラキュウコン'),
                ('ウォッシュロトム','ヒートロトム'),
                ('イダイトウ(オス)','イダイトウ(メス)'),
            ):
                for i, name in enumerate([first, second, 'カバルドン',
                                          'サーフゴー', 'ドドゲザン', 'ミミッキュ']):
                    page.locator(f'#foe{i}').fill(name)
                page.locator('#analyze').click()
                assert '同じポケモンが重複' in page.locator('#status').inner_text()
                assert page.locator('#result .hero').count() == 0

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
            # Official 2026-08-05 M-B additions: catalog coverage is not
            # matchup coverage, nor a completed M-C eligibility audit.
            assert page.evaluate("() => officialMbAdditions.length") == 22
            assert page.evaluate("""() => officialMbAdditions.every(
                name => Array.from(document.querySelectorAll('#dex option'),
                    option => option.value).includes(name))""")
            assert page.evaluate("""() => new Set(Array.from(
                document.querySelectorAll('#dex option'), o => o.value)).size ===
                document.querySelectorAll('#dex option').length""")
            assert '公式M-B追加22種' in page.locator('#count + p').inner_text()
            assert '2026-08-05' in page.locator('#count + p').inner_text()
            assert '現行M-C使用可否の全件照合は未完了' in page.locator('#count + p').inner_text()
            # All Mega forms listed by the official M-A/M-B/M-C regulations
            # must be independently selectable. These are catalog entries,
            # NOT proof of a safe matchup or a completed 352-form audit.
            assert page.evaluate("() => [officialMegaMa.length, officialMegaMb.length, officialMegaMc.length]") == [59, 16, 6]
            assert page.evaluate("() => officialMegaForms.length") == 81
            # Every eligible Mega needs its ordinary pre-Mega species available
            # as a distinct input candidate, without implying matchup evidence.
            assert page.evaluate("() => officialMegaBaseCandidates.length") == 76
            assert page.evaluate("""() => officialMegaBaseCandidates.every(name =>
                Array.from(document.querySelectorAll('#dex option'), o => o.value).includes(name))""")
            assert page.evaluate("() => document.querySelectorAll('#dex option').length") >= 229
            assert '対応する通常種76件' in page.locator('#count + p').inner_text()
            for species in ('スピアー', 'ピジョット', 'ユキメノコ',
                            'メガニウム', 'エンブオー', 'フラエッテ'):
                assert page.locator('#dex option').evaluate_all(
                    "(els, name) => els.some(el => el.value === name)", species
                ), f'Missing pre-Mega candidate: {species}'
            for i, name in enumerate(('スピアー', 'ピジョット', 'ユキメノコ',
                                       'メガニウム', 'エンブオー', 'フラエッテ')):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#analyze').click()
            assert page.locator('#result .candidate-unverified').count() == 0
            assert page.locator('#result .abstention-banner').count() == 1
            assert page.locator('#result .hero').count() == 0
            assert '検証済み対面 0/6匹' in page.locator('#result .evidence-summary').inner_text()
            assert page.evaluate("""() => new Set(officialMegaForms.map(formKey)).size === 81 &&
                officialMegaForms.every(name => Array.from(
                    document.querySelectorAll('#dex option'), o => o.value).includes(name))""")
            assert page.evaluate("() => megaBaseNames.has(normalize('ユキメノコ'))")
            assert page.evaluate("() => megaBaseNames.has(normalize('スピアー'))")
            assert '公式M-A/B/Cメガ形態81件' in page.locator('#count + p').inner_text()
            # Meganium is a NORMAL species whose name begins with "メガ".
            # Only the cataloged "メガメガニウム" is a Mega form.
            assert page.evaluate("() => normalize('メガニウム') === 'メガニウム'")
            assert page.evaluate("() => normalize('メガメガニウム') === 'メガニウム'")
            assert page.evaluate("() => !isMegaForm('メガニウム') && isMegaForm('メガメガニウム')")
            assert page.evaluate("() => megaBaseNames.has(normalize('メガニウム'))")
            meganium_foes = ['メガニウム','カバルドン','サーフゴー',
                             'ドドゲザン','アシレーヌ','ミミッキュ']
            for i, name in enumerate(meganium_foes):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#analyze').click()
            assert page.locator('#result .abstention-banner').count() == 1
            assert page.locator('#result .hero').count() == 0
            assert 'メガニウム' in page.locator('#result .mega-base-unverified').inner_text()
            assert page.locator('#result .mega-form-unverified').count() == 0
            assert 'メガニウム' in page.locator('#result .mega-uncertainty').inner_text()
            page.locator('#foe0').fill('メガメガニウム')
            page.locator('#analyze').click()
            assert 'メガメガニウム' in page.locator('#result .mega-form-unverified').inner_text()
            assert page.locator('#result .mega-base-unverified').count() == 0
            page.locator('#foe1').fill('メガニウム')
            page.locator('#analyze').click()
            assert '同じポケモンが重複' in page.locator('#status').inner_text()

            newly_listed_megas = ['メガスピアー', 'メガピジョット', 'メガユキメノコ',
                                   'メガライチュウY', 'メガラグラージ', 'メガキラフロル']
            for i, name in enumerate(newly_listed_megas):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#analyze').click()
            assert page.locator('#result .candidate-unverified').count() == 0
            assert page.locator('#result .abstention-banner').count() == 1
            assert page.locator('#result .hero').count() == 0
            assert all(name in page.locator('#result .mega-uncertainty').inner_text()
                       for name in newly_listed_megas)
            # Newly identified base-form Mega possibilities must also be warned,
            # even though no reviewed matchup records exist yet.
            base_mega_case = ['スピアー','ユキメノコ','ピジョット',
                              'ジュカイン','カバルドン','アシレーヌ']
            for i, name in enumerate(base_mega_case):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#analyze').click()
            assert page.locator('#result .abstention-banner').count() == 1
            assert page.locator('#result .hero').count() == 0
            assert all(name in page.locator('#result .mega-uncertainty').inner_text()
                       for name in base_mega_case[:4])
            unverified_mb = ['ラフレシア','ハリーセン','ムクホーク',
                             'ムシャーナ','ペンドラー','シビルドン']
            for i, name in enumerate(unverified_mb):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#analyze').click()
            assert page.locator('#result .candidate-unverified').count() == 0
            assert page.locator('#result .abstention-banner').count() == 1
            assert page.locator('#result .hero').count() == 0
            assert '0/6匹' in page.locator('#result .risk-banner').inner_text()
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
            # Two named answers do not justify a pick while four threats are unknown.
            two_answers = ['ゴリランダー','ドドゲザン','ガブリアス',
                           'ウルガモス','エースバーン','ドラパルト']
            for i, name in enumerate(two_answers):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#analyze').click()
            assert page.locator('#result .abstention-banner').count() == 1
            assert page.locator('#result .hero').count() == 0
            assert '2/6匹' in page.locator('#result .evidence-summary').inner_text()
            assert '選出判断を保留' in page.locator('#result .risk-banner').inner_text()
            # A manual name outside the incomplete M-C candidate catalog must
            # not inherit a recommendation from the other five known names.
            high_coverage = ['アシレーヌ','ドドゲザン','サーフゴー',
                             'ミミッキュ','カバルドン']
            unknown_input = ['未照合ポケモン', *high_coverage]
            assert page.evaluate('(names) => recommend(names).comparisonSummary.total', unknown_input) >= 4
            for i, name in enumerate(unknown_input):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#analyze').click()
            assert page.locator('#result .candidate-unverified').count() == 1
            assert page.locator('#result .abstention-banner').count() == 1
            assert page.locator('#result .hero').count() == 0
            # An autocomplete-listed normal form is not a validated matchup.
            # Even five named answers cannot make its unknown lead safe.
            listed_unknown = ['ガブリアス', *high_coverage]
            assert page.locator('#dex option').evaluate_all(
                "(els) => els.some(el => el.value === 'ガブリアス')")
            assert page.evaluate('(names) => recommend(names).comparisonSummary.total', listed_unknown) == 5
            for i, name in enumerate(listed_unknown):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#analyze').click()
            assert page.locator('#result .abstention-banner').count() == 1
            assert page.locator('#result .hero').count() == 0
            assert 'ガブリアス' in page.locator('#result .risk-banner').inner_text()
            assert '5/6匹' in page.locator('#result .evidence-summary').inner_text()
            assert page.locator('#result .candidate-unverified').count() == 0
            # Mega X and even name-registered Mega Salamence are not verified
            # matchups; a high name-only score must not imply a safe trio.
            for mega in ('メガリザードンX', 'メガボーマンダ'):
                mega_case = [mega, *high_coverage]
                assert page.evaluate('(names) => recommend(names).comparisonSummary.total', mega_case) >= 4
                for i, name in enumerate(mega_case):
                    page.locator(f'#foe{i}').fill(name)
                page.locator('#analyze').click()
                assert page.locator('#result .mega-form-unverified').count() == 1, mega
                assert page.locator('#result .abstention-banner').count() == 1, mega
                assert page.locator('#result .hero').count() == 0, mega
                assert all(name in page.locator('#result').inner_text() for name in mega_case)
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
            # Two actual answers are still insufficient with four unknown opponents.
            for i, name in enumerate(two_answers):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#analyze').click()
            assert page.locator('#result .abstention-banner').count() == 1
            assert page.locator('#result .hero').count() == 0
            assert '選出3匹の対応 2/6匹' in page.locator('#result .evidence-summary').inner_text()
            # Tier-1 Mega candidates without matchup verification must override
            # otherwise plentiful (5/6) name-only answers. This is particularly
            # important for a normal-form name that may Mega evolve.
            for danger in ('リザードン', 'メガリザードンY',
                           'ゲンガー', 'メガゲンガー',
                           'グソクムシャ', 'メガグソクムシャ'):
                critical_case = [danger, 'アシレーヌ', 'ドドゲザン',
                                 'サーフゴー', 'ミミッキュ', 'カバルドン']
                assert page.evaluate('(names) => recommend(names).comparisonSummary.total', critical_case) == 5
                for i, name in enumerate(critical_case):
                    page.locator(f'#foe{i}').fill(name)
                page.locator('#analyze').click()
                assert page.locator('#result .abstention-banner').count() == 1, danger
                assert page.locator('#result .hero').count() == 0, danger
                critical_text = page.locator('#result .critical-uncertainty').inner_text()
                assert danger in critical_text and '未検証' in critical_text, critical_text
                assert '2026-10-27' in critical_text, critical_text
                assert danger in page.locator('#result .mega-uncertainty').inner_text()
                assert '5/6匹' in page.locator('#result .evidence-summary').inner_text()
            assert page.evaluate("() => megaCandidatesFor(['リザードン','ゲンガー']).length") == 2

            # Psychic Surge invalidates priority-based cleanup even when all
            # five OTHER opponents have name-only matchup answers.
            for indeedee in ('イエッサン', 'イエッサン(オス)', 'イエッサン(メス)'):
                terrain_case = [indeedee, 'アシレーヌ', 'ドドゲザン',
                                'サーフゴー', 'ミミッキュ', 'カバルドン']
                assert page.evaluate('(names) => recommend(names).comparisonSummary.total', terrain_case) == 5
                for i, name in enumerate(terrain_case):
                    page.locator(f'#foe{i}').fill(name)
                page.locator('#analyze').click()
                assert page.locator('#result .abstention-banner').count() == 1, indeedee
                assert page.locator('#result .hero').count() == 0, indeedee
                warning = page.locator('#result .terrain-uncertainty').inner_text()
                assert indeedee in warning and 'サイコフィールド' in warning, warning
                assert '2026-10-28' in warning and '未検証' in warning
                assert all(name in page.locator('#result').inner_text() for name in terrain_case)
            for i, name in enumerate(two_answers):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#analyze').click()
            assert page.locator('#result .terrain-uncertainty').count() == 0
            assert page.locator('#result .abstention-banner').count() == 1
            assert page.locator('#result .hero').count() == 0

            for names in CASES:
                for i,name in enumerate(names):
                    page.locator(f'#foe{i}').fill(name)
                page.locator('#analyze').click()
                assert page.locator('#result').is_visible(), f'No result: {names}'
                selected = page.evaluate('(names) => recommend(names).comparisonSummary.chosen', names)
                assert page.locator('#result .abstention-banner').count() == 1
                assert page.locator('#result .hero').count() == 0
                assert page.locator('#result .matchup-unverified').count() == 1
                assert '検証済み対面 0/6匹' in page.locator('#result .evidence-summary').inner_text()
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2'), 'Horizontal overflow'

            # A recommendation must use only the six configured team members.
            roster = {'カバルドン','メガルカリオZ','メガカイリュー','ミミッキュ','ギルガルド','イダイトウ♂'}
            for names in CASES:
                for i, name in enumerate(names):
                    page.locator(f'#foe{i}').fill(name)
                page.locator('#analyze').click()
                chosen = page.locator('#result .hero .chip').all_inner_texts()
                selected = page.evaluate('(names) => recommend(names).comparisonSummary.chosen', names)
                assert chosen == [], 'Must not display an unverified trio'
                assert page.locator('#result .abstention-banner').count() == 1
                decision = page.evaluate('(names) => recommend(names)', names)
                assert len(decision['team']) == 3 and len(set(decision['team'])) == 3
                assert all(name in roster for name in decision['team'])
                assert decision['lead'] in decision['team']
                result_text = page.locator('#result').inner_text()
                assert all(name in result_text for name in names), 'Opponent coverage must mention all six inputs'
            # Lead safety regression: do not recommend Hippowdon into obvious
            # Rillaboom / Pelipper lead pressure when a fallback is selected.
            for danger in ('ゴリランダー', 'ペリッパー'):
                names = [danger,'ガブリアス','ウルガモス','エースバーン','ドドゲザン','ドラパルト']
                for i, name in enumerate(names):
                    page.locator(f'#foe{i}').fill(name)
                page.locator('#analyze').click()
                decision = page.evaluate('(names) => recommend(names)', names)
                lead = decision['lead']
                assert lead in decision['team'], f'Lead must be one of the selected trio: {lead}'
                assert lead != 'カバルドン', f'Unsafe Hippowdon lead vs {danger}'
                assert any('先発変更' in note for note in decision['cautions']), f'Missing safety explanation vs {danger}'
                assert page.locator('#result .abstention-banner').count() == 1
                assert page.locator('#result .hero').count() == 0
            # Without those specific dangers, preserve the article's baseline lead.
            safe_names = ['ガブリアス','ゲンガー','エースバーン','ドラパルト','ルカリオ','サザンドラ']
            assert page.evaluate('(names) => recommend(names).lead', safe_names) == 'カバルドン'

            # Six registered names are NOT enough if the selected three lack
            # an answer for even one of the six opponents.
            known_names = ['ミミッキュ','ドドゲザン','ペリッパー','アシレーヌ','サーフゴー','カバルドン']
            assert page.evaluate('(names) => recommend(names).comparisonSummary.total', known_names) == 6
            assert page.evaluate('(names) => recommend(names).comparisonSummary.chosen', known_names) < 6
            for i, name in enumerate(known_names):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#analyze').click()
            banner = page.locator('#result .risk-banner')
            assert banner.count() == 1 and '6/6匹' in banner.inner_text(), banner.inner_text()
            assert page.locator('#result .abstention-banner').count() == 1
            assert page.locator('#result .hero').count() == 0
            assert page.locator('#result .abstention-coverage').count() == 1
            assert page.locator('#result .abstention-coverage .line').count() > 0
            assert page.locator('#result .mega-base-unverified').count() == 0
            # Even a six-of-six name-rule match is NOT a verified matchup.
            # It must not unlock a trio or lead until form-specific evidence exists.
            fully_answered = ['ドヒドイデ','ラッキー','ハピナス','ブラッキー','クレセリア','サーフゴー']
            assert page.evaluate('(names) => recommend(names).comparisonSummary.chosen', fully_answered) == 6
            for i, name in enumerate(fully_answered):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#analyze').click()
            assert page.locator('#result .hero .chip').count() == 0
            assert page.locator('#result .abstention-banner').count() == 1
            assert page.locator('#result .matchup-unverified').count() == 1
            assert '検証済み対面 0/6匹' in page.locator('#result .evidence-summary').inner_text()
            assert all(name in page.locator('#result .matchup-unverified').inner_text() for name in fully_answered)
            assert page.evaluate('() => Object.keys(verifiedMatchupEvidence).length') == 0
            # Name coverage 6/6 does not validate base-to-Mega branching.
            # Banette, Sableye and Salamence previously bypassed the explicit
            # Mega-form gate when entered in their normal forms.
            for base_mega in ('ジュペッタ', 'ヤミラミ', 'ボーマンダ'):
                mega_case = [base_mega, 'ミミッキュ', 'ドドゲザン',
                             'ペリッパー', 'アシレーヌ', 'サーフゴー']
                for i, name in enumerate(mega_case):
                    page.locator(f'#foe{i}').fill(name)
                page.locator('#analyze').click()
                assert '6/6匹' in page.locator('#result .risk-banner').inner_text(), base_mega
                assert page.locator('#result .abstention-banner').count() == 1, base_mega
                assert page.locator('#result .hero').count() == 0, base_mega
                assert base_mega in page.locator('#result .mega-base-unverified').inner_text()
                assert base_mega in page.locator('#result .mega-uncertainty').inner_text()
            # The same six-name case still abstains after other checks.
            for i, name in enumerate(known_names):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#analyze').click()
            assert page.locator('#result .hero').count() == 0
            assert page.locator('#result .abstention-banner').count() == 1

            unknown_names = ['ガブリアス','ウルガモス','ドラパルト','キラフロル','エースバーン','ゲッコウガ']
            for i, name in enumerate(unknown_names):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#analyze').click()
            banner = page.locator('#result .risk-banner')
            assert '0/6匹' in banner.inner_text(), banner.inner_text()
            assert all(name in banner.inner_text() for name in unknown_names), 'Missing unknown names in risk banner'
            assert '選出判断を保留' in banner.inner_text(), 'Must not present unknown coverage as validated'
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
            # The abstention view shows the separate candidate-coverage metric
            # instead of the expanded recommendation-only detail section.
            assert '入力候補' in page.locator('#result .evidence-summary').inner_text()
            assert '全件照合未完了' in page.locator('#result .evidence-summary').inner_text()

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
