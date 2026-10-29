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
            assert page.locator('#analyze').inner_text() == 'リスクを確認'
            assert page.locator('.slot-source').count() == 6
            assert '選出3匹・先発の推奨は保留' in page.locator('.sub').first.inner_text()

            # Official 2026 M-A Global Challenge roster: 31 distinct forms,
            # including region, sex and family-size variants (historical
            # eligibility only; M-C audit remains incomplete).
            assert page.evaluate("() => officialMaSpecialRoster.length") == 31
            assert page.evaluate("""() => officialMaSpecialRoster.every(
                name => Array.from(document.querySelectorAll('#dex option'),
                    option => option.value).includes(name))""")
            assert page.evaluate("() => historicalMaTournamentCandidates.length") == 41
            assert page.evaluate("() => historicalMaTournamentMoreCandidates.length") == 63
            assert page.evaluate("() => document.querySelectorAll('#dex option').length") == 348
            assert page.evaluate("""() => officialMcRosterKnownForms.every(name =>
                Array.from(document.querySelectorAll('#dex option'), o => o.value).includes(name))""")
            assert page.evaluate("() => officialMcRosterKnownForms.length") == 14
            assert page.evaluate("""() => Array.from(officialMcExcludedCandidates).every(name =>
                !Array.from(document.querySelectorAll('#dex option'), o => o.value).includes(name))""")
            assert page.evaluate("() => officialMcExcludedCandidates.size") == 19
            assert page.evaluate("() => requiredMatchupForms('イッカネズミ').length") == 2
            assert page.evaluate("() => requiredMatchupForms('イキリンコ').length") == 4
            assert page.evaluate("() => officialMcSpecialForms.length") == 2
            assert page.evaluate("""() => officialMcSpecialForms.every(name =>
                Array.from(document.querySelectorAll('#dex option'), o => o.value).includes(name))""")
            assert page.evaluate("() => requiredMatchupForms('ヤバソチャ').length") == 2
            # Generic species previews must cover all playable sex / size /
            # named forms. An exact form must not inherit its sibling's data.
            generic_branches = {
                'イエッサン': ['イエッサン(オス)', 'イエッサン(メス)'],
                'イダイトウ': ['イダイトウ(オス)', 'イダイトウ(メス)'],
                'ストリンダー': ['ストリンダー(ハイ)', 'ストリンダー(ロー)'],
                'ルガルガン': ['ルガルガン(まひる)', 'ルガルガン(まよなか)', 'ルガルガン(たそがれ)'],
                'パンプジン': ['パンプジン(こだま)', 'パンプジン(ちゅうだま)',
                           'パンプジン(おおだま)', 'パンプジン(ギガだま)'],
            }
            for species, forms in generic_branches.items():
                actual = page.evaluate("(name) => requiredMatchupForms(name)", species)
                assert set(actual) == set(forms), (species, actual)
                for form in forms:
                    assert page.evaluate("(name) => requiredMatchupForms(name)", form) == [form]
            assert set(page.evaluate("() => requiredMatchupForms('ニャオニクス')")) == {
                'ニャオニクス(オス)', 'ニャオニクス(メス)',
                'メガニャオニクス(オス)', 'メガニャオニクス(メス)'
            }
            assert page.evaluate("() => requiredMatchupForms('ニャオニクス(オス)')") == [
                'ニャオニクス(オス)', 'メガニャオニクス(オス)'
            ]
            assert page.evaluate("() => requiredMatchupForms('ニャオニクス(メス)')") == [
                'ニャオニクス(メス)', 'メガニャオニクス(メス)'
            ]
            assert page.evaluate("() => !megaCandidatesFor(['イッカネズミ','イキリンコ']).length")

            assert page.evaluate("() => formKey('ロトム (フロストロトム)') === 'フロストロトム'")
            assert page.evaluate("() => formKey('ケンタロス (パルデアのすがた・コンバットしゅ)') === 'パルデアケンタロス(かくとう)'")
            assert '過去のM-A大会参加可能リスト由来104形態' in page.locator('#count + p').inner_text()
            assert '現行M-C未照合' in page.locator('#count + p').inner_text()
            # Exhaustive catalog smoke: every listed form must be accepted as
            # one of six distinct species, never silently unlock a trio/lead.
            # Run in one browser evaluation to keep CI fast on mobile + desktop.
            audit = page.evaluate("""() => {
                const options = Array.from(document.querySelectorAll('#dex option'), o => o.value);
                const baseline = ['カバルドン','アシレーヌ','サーフゴー',
                                  'ガブリアス','ミミッキュ','ドドゲザン'];
                for (const candidate of options) {
                    const others = baseline.filter(name => normalize(name) !== normalize(candidate)).slice(0, 5);
                    const names = [candidate, ...others];
                    if (names.length !== 6 || new Set(names.map(normalize)).size !== 6)
                        return {candidate, reason: 'species identity collision'};
                    fields.forEach((field, i) => {field.value = names[i]});
                    analyze();
                    if (document.querySelector('#status').textContent ||
                        !document.querySelector('#result .abstention-banner') ||
                        document.querySelector('#result .hero'))
                        return {candidate, reason: 'invalid input or unsafe recommendation'};
                }
                return {checked: options.length};
            }""")
            assert audit == {'checked': 348}, audit
            # Historical M-A regional forms share a species slot but retain
            # distinct form identities for any future matchup evidence.
            for regional, ordinary in (
                ('アローラライチュウ', 'ライチュウ'),
                ('ヒスイウインディ', 'ウインディ'),
                ('ガラルヤドラン', 'ヤドラン'),
                ('ガラルヤドキング', 'ヤドキング'),
                ('ヒスイバクフーン', 'バクフーン'),
                ('ヒスイダイケンキ', 'ダイケンキ'),
                ('パルデアケンタロス(かくとう)', 'ケンタロス'),
                ('ヒスイゾロアーク', 'ゾロアーク'),
                ('ヒスイヌメルゴン', 'ヌメルゴン'),
                ('ガラルマッギョ', 'マッギョ'),
                ('ヒスイクレベース', 'クレベース'),
                ('ヒスイジュナイパー', 'ジュナイパー'),
            ):
                assert page.evaluate("(pair) => normalize(pair[0]) === normalize(pair[1])",
                                     [regional, ordinary]), regional
                assert page.evaluate("(pair) => formKey(pair[0]) !== formKey(pair[1])",
                                     [regional, ordinary]), regional
            assert page.evaluate("() => formKey('イエッサン♀') === formKey('イエッサン(メス)')")
            assert page.evaluate("() => formKey('パルデアケンタロス(炎)') === formKey('パルデアケンタロス(ほのお)')")
            assert '公式M-A特別セレクト31形態' in page.locator('#count + p').inner_text()
            assert '公式M-C全件監査2026-10-29成功' in page.locator('#count + p').inner_text()
            ma_new = ['アローラキュウコン','コータス','エルフーン',
                      'ニャオニクス(メス)','イダイトウ(オス)','イッカネズミ(3びき)']
            for i, name in enumerate(ma_new):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#analyze').click()
            assert page.locator('#result .candidate-unverified').count() == 0
            assert page.locator('#result .abstention-banner').count() == 1
            assert page.locator('#result .hero').count() == 0
            assert '検証済み対面 0/6匹' in page.locator('#result .evidence-summary').inner_text()

            # Provenance must distinguish official M-C additions from historical
            # M-A candidates; neither a catalog entry nor a source link is
            # evidence of a verified matchup.
            audit_text = page.locator('#catalog-audit').inner_text()
            assert '348形態' in audit_text
            assert '公式M-C全件照合2026-10-29成功' in audit_text
            assert '検証済み対面 0/348形態' in audit_text
            for name, label in (
                ('グソクムシャ', '公式M-C追加'),
                ('メガグソクムシャ', '公式M-Cメガ追加'),
                ('サーフゴー', '公式M-B追加'),
                ('アーボック', '過去M-A大会由来'),
                ('未照合ポケモン', '候補外'),
            ):
                actual = page.evaluate('(n) => candidateProvenance(n).label', name)
                assert label in actual, (name, actual)
            provenance_case = ['グソクムシャ','メガアブソルZ','アーボック',
                               'サーフゴー','カバルドン','未照合ポケモン']
            for i, name in enumerate(provenance_case):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#analyze').click()
            assert page.locator('#result .abstention-banner').count() == 1
            assert page.locator('#result .hero').count() == 0
            assert page.locator('#result .candidate-provenance').count() == 6
            assert '過去M-A大会由来' in page.locator('#result .candidate-provenance').all_inner_texts()[2]
            assert '候補外' in page.locator('#result .candidate-provenance').all_inner_texts()[5]

            # Full regional names must map to the same exact form, not to
            # a different form or an automatically validated matchup.
            for full, short in (
                ('ライチュウ（アローラのすがた）','アローラライチュウ'),
                ('ウインディ（ヒスイのすがた）','ヒスイウインディ'),
                ('ヤドラン（ガラルのすがた）','ガラルヤドラン'),
                ('ヤドキング（ガラルのすがた）','ガラルヤドキング'),
                ('バクフーン（ヒスイのすがた）','ヒスイバクフーン'),
                ('ダイケンキ（ヒスイのすがた）','ヒスイダイケンキ'),
                ('ゾロアーク（ヒスイのすがた）','ヒスイゾロアーク'),
                ('ヌメルゴン（ヒスイのすがた）','ヒスイヌメルゴン'),
                ('マッギョ（ガラルのすがた）','ガラルマッギョ'),
                ('クレベース（ヒスイのすがた）','ヒスイクレベース'),
                ('ジュナイパー（ヒスイのすがた）','ヒスイジュナイパー'),
            ):
                assert page.evaluate('(pair) => formKey(pair[0]) === formKey(pair[1])',
                                     [full, short]), (full, short)
                assert page.evaluate('(pair) => normalize(pair[0]) === normalize(pair[1])',
                                     [full, short]), (full, short)
            page.locator('#foe0').fill('ウインディ（ヒスイのすがた）')
            assert '過去M-A大会由来' in page.locator('#source0').inner_text()
            page.locator('#foe1').fill('グソクムシャ')
            assert '公式M-C追加' in page.locator('#source1').inner_text()
            page.locator('#foe2').fill('未照合ポケモン')
            assert '候補外' in page.locator('#source2').inner_text()
            page.reload(wait_until='domcontentloaded')
            assert page.locator('#foe0').input_value() == 'ウインディ（ヒスイのすがた）'
            assert '過去M-A大会由来' in page.locator('#source0').inner_text()
            page.locator('#clear').click()
            assert page.locator('#source0').inner_text() == '未入力'
            for i, name in enumerate(('ヒスイウインディ','ウインディ（ヒスイのすがた）',
                                      'カバルドン','サーフゴー','ミミッキュ','ドドゲザン')):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#analyze').click()
            assert '同じポケモンが重複' in page.locator('#status').inner_text()
            assert page.locator('#result .hero').count() == 0

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
            # feather forms. Do not confuse the 35 additions with all official M-C eligible forms.
            assert page.evaluate("() => officialMcAdditions.length") == 35
            # Independent snapshot from the official M-C standard select (29)
            # and M-C Mega regulation update (6), both dated 2026-09-09.
            # Exact set equality catches missing, duplicated and spurious names;
            # it does NOT certify the complete M-C eligible roster.
            official_mc_delta = [
                'プクリン','ペルシアン','アローラペルシアン','カモネギ',
                'バリヤード','マルノーム','ボーマンダ','ゴーゴート',
                'グソクムシャ','ゴリランダー','エースバーン','インテレオン',
                'フォクスライ','ストリンダー(ハイ)','ストリンダー(ロー)',
                'オトスパス','ニャイキング','ネギガナイト','バチンウニ',
                'イエッサン(オス)','イエッサン(メス)','パーモット',
                'オリーヴァ','イキリンコ(グリーンフェザー)',
                'イキリンコ(ブルーフェザー)','イキリンコ(イエローフェザー)',
                'イキリンコ(ホワイトフェザー)','マフィティフ','セグレイブ',
                'メガアブソルZ','メガボーマンダ','メガガブリアスZ',
                'メガルカリオZ','メガグソクムシャ','メガセグレイブ',
            ]
            actual_mc_delta = page.evaluate("() => officialMcAdditions")
            assert len(actual_mc_delta) == len(set(actual_mc_delta)) == 35
            assert set(actual_mc_delta) == set(official_mc_delta), (
                'Official M-C delta differs: missing=' +
                str(sorted(set(official_mc_delta) - set(actual_mc_delta))) +
                ', unexpected=' +
                str(sorted(set(actual_mc_delta) - set(official_mc_delta)))
            )
            assert '公式M-C追加分 35/35形態を候補登録' in page.locator('#catalog-audit').inner_text()
            assert '公式M-C全件照合2026-10-29成功' in page.locator('#catalog-audit').inner_text()
            assert page.locator('#catalog-audit a').get_attribute('href') == (
                'https://web-view.app.pokemonchampions.jp/battle/pages/'
                'events/rs178713870219xeaaio/ja/pokemon.html'
            )
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
            assert '公式M-C全件監査2026-10-29成功' in page.locator('#count + p').inner_text()
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
            assert '公式M-C全件監査2026-10-29成功' in page.locator('#count + p').inner_text()
            # All Mega forms listed by the official M-A/M-B/M-C regulations
            # must be independently selectable. These are catalog entries,
            # NOT proof of a safe matchup or a completed official M-C audit.
            assert page.evaluate("() => [officialMegaMa.length, officialMegaMb.length, officialMegaMc.length]") == [59, 16, 6]
            assert page.evaluate("() => officialMegaForms.length") == 81
            assert page.evaluate("() => megaInputForms.length") == 82
            assert page.evaluate("() => new Set(megaInputForms.map(formKey)).size") == 82
            assert page.evaluate("() => !megaInputForms.includes('メガニャオニクス')")
            assert page.evaluate("() => megaMeowsticSexForms.length") == 2
            assert page.evaluate("() => separatelyDocumentedForms.length") == 1
            assert page.evaluate("() => formKey('フラエッテ(えいえんのはな)') !== formKey('フラエッテ')")
            assert page.evaluate("() => formKey('フラエッテ(えいえんのはな)') !== formKey('メガフラエッテ')")
            assert page.evaluate("() => normalize('フラエッテ(えいえんのはな)') === normalize('メガフラエッテ')")
            assert page.locator('#dex option').evaluate_all(
                "(els) => els.some(el => el.value === 'フラエッテ(えいえんのはな)')")
            page.locator('#foe0').fill('フラエッテ(えいえんのはな)')
            assert 'GameWith個別掲載' in page.locator('#source0').inner_text()
            for i, name in enumerate(('フラエッテ(えいえんのはな)','カバルドン',
                                      'サーフゴー','ミミッキュ','ドドゲザン','アシレーヌ')):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#analyze').click()
            assert page.locator('#result .abstention-banner').count() == 1
            assert page.locator('#result .hero').count() == 0
            assert 'GameWith個別掲載' in page.locator('#result .candidate-provenance').first.inner_text()
            assert page.evaluate("() => formKey('メガニャオニクス♂') === formKey('メガニャオニクス(オス)')")
            assert page.evaluate("() => formKey('メガニャオニクス♀') === formKey('メガニャオニクス(メス)')")
            assert page.evaluate("() => formKey('メガニャオニクス(オス)') !== formKey('メガニャオニクス(メス)')")
            assert page.evaluate("() => normalize('メガニャオニクス(オス)') === normalize('ニャオニクス(メス)')")
            assert page.evaluate("() => megaMeowsticSexForms.every(isMegaForm)")
            for i, name in enumerate(('メガニャオニクス(オス)','メガニャオニクス(メス)',
                                      'カバルドン','サーフゴー','ミミッキュ','ドドゲザン')):
                page.locator(f'#foe{i}').fill(name)
            assert '公式M-Aメガ' in page.locator('#source0').inner_text()
            page.locator('#analyze').click()
            assert '同じポケモンが重複' in page.locator('#status').inner_text()
            page.locator('#foe1').fill('アシレーヌ')
            page.locator('#analyze').click()
            assert page.locator('#result .abstention-banner').count() == 1
            assert page.locator('#result .hero').count() == 0
            assert 'メガニャオニクス(オス)' in page.locator('#result .mega-form-unverified').inner_text()
            # Every eligible Mega needs its ordinary pre-Mega species available
            # as a distinct input candidate, without implying matchup evidence.
            assert page.evaluate("() => officialMegaBaseCandidates.length") == 76
            assert page.evaluate("""() => officialMegaBaseCandidates.every(name => officialMcExcludedCandidates.has(name) ||
                Array.from(document.querySelectorAll('#dex option'), o => o.value).includes(name))""")
            assert page.evaluate("() => document.querySelectorAll('#dex option').length") >= 229
            assert '対応する通常種候補76件（未指定・対象外形態2件除外）' in page.locator('#count + p').inner_text()
            for species in ('スピアー', 'ピジョット', 'ユキメノコ',
                            'メガニウム', 'エンブオー', 'フラエッテ(えいえんのはな)'):
                assert page.locator('#dex option').evaluate_all(
                    "(els, name) => els.some(el => el.value === name)", species
                ), f'Missing pre-Mega candidate: {species}'
            for i, name in enumerate(('スピアー', 'ピジョット', 'ユキメノコ',
                                       'メガニウム', 'エンブオー', 'フラエッテ(えいえんのはな)')):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#analyze').click()
            assert page.locator('#result .candidate-unverified').count() == 0
            assert page.locator('#result .abstention-banner').count() == 1
            assert page.locator('#result .hero').count() == 0
            assert '検証済み対面 0/6匹' in page.locator('#result .evidence-summary').inner_text()
            assert page.evaluate("""() => new Set(megaInputForms.map(formKey)).size === 82 &&
                megaInputForms.every(name => Array.from(
                    document.querySelectorAll('#dex option'), o => o.value).includes(name))""")
            assert page.evaluate("() => requiredMatchupForms('ユキメノコ').length > 1")
            assert page.evaluate("() => requiredMatchupForms('スピアー').length > 1")
            assert '公式M-A/B/Cメガ81名称・性差込み82形態' in page.locator('#count + p').inner_text()
            # Meganium is a NORMAL species whose name begins with "メガ".
            # Only the cataloged "メガメガニウム" is a Mega form.
            assert page.evaluate("() => normalize('メガニウム') === 'メガニウム'")
            assert page.evaluate("() => normalize('メガメガニウム') === 'メガニウム'")
            assert page.evaluate("() => !isMegaForm('メガニウム') && isMegaForm('メガメガニウム')")
            assert page.evaluate("() => requiredMatchupForms('メガニウム').length > 1")
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
            # Fail-closed schema: a dated source and a matching name are not
            # enough. Every known form branch needs a reviewed lead response.
            gate = page.evaluate("""() => {
              const source='https://example.org/reviewed',updated='2026-10-28';
              const cited={source,updated};
              const record={...cited,form:'ドヒドイデ',reviewed:true,formReviewed:true,
                branchScope:'all-known',
                variants:[{...cited,id:'normal',form:'ドヒドイデ',reviewed:true,
                  ability:'さいせいりょく',speedBase:35,
                  speedRangeReviewed:true,speedMin:45,speedMax:95,
                  moveCoverageReviewed:true,moves:['どくどく','じこさいせい'],
                  itemCoverageReviewed:true,items:['くろいヘドロ'],
                  priorityMoves:[]}],
                answers:[{...cited,variant:'normal',pokemon:'カバルドン',
                  reason:'synthetic schema fixture, not a real matchup',reviewed:true}],
                leadChecks:[{...cited,variant:'normal',lead:'カバルドン',
                  response:'stay',reason:'synthetic schema fixture',reviewed:true}]};
              const team=['カバルドン','ミミッキュ','メガルカリオZ'];
              const check=r=>hasVerifiedMatchupAnswer(r,'ドヒドイデ',team,'カバルドン');
              return {
                complete:check(record),
                oldNameOnly:check({...cited,reviewed:true,answers:['カバルドン']}),
                wrongForm:hasVerifiedMatchupAnswer(record,'メガドヒドイデ',team,'カバルドン'),
                wrongLead:hasVerifiedMatchupAnswer(record,'ドヒドイデ',team,'ミミッキュ'),
                unsafe:check({...record,leadChecks:[{...record.leadChecks[0],response:'unsafe'}]}),
                conflictingLead:check({...record,leadChecks:[...record.leadChecks,
                  {...record.leadChecks[0],response:'unsafe'}]}),
                duplicateLead:check({...record,leadChecks:[...record.leadChecks,
                  {...record.leadChecks[0]}]}),
                shadowTagTrapped:check({...record,variants:[{
                  ...record.variants[0],ability:'かげふみ'}],
                  answers:[{...record.answers[0],pokemon:'ミミッキュ'}],
                  leadChecks:[{...record.leadChecks[0],response:'switch',switchTo:'ミミッキュ'}]}),
                shadowTagGhostCanSwitch:hasVerifiedMatchupAnswer({...record,
                  variants:[{...record.variants[0],ability:'かげふみ'}],
                  leadChecks:[{...record.leadChecks[0],lead:'ミミッキュ',
                    response:'switch',switchTo:'カバルドン'}]},
                  'ドヒドイデ',team,'ミミッキュ'),
                // Basculegion is Water/Ghost and may switch despite Shadow Tag.
                shadowTagBasculegionCanSwitch:hasVerifiedMatchupAnswer({...record,
                  variants:[{...record.variants[0],ability:'かげふみ'}],
                  leadChecks:[{...record.leadChecks[0],lead:'イダイトウ♂',
                    response:'switch',switchTo:'カバルドン'}]},
                  'ドヒドイデ',['カバルドン','イダイトウ♂','ミミッキュ'],'イダイトウ♂'),
                // A trapped non-Ghost cannot switch TO a Ghost teammate.
                shadowTagCannotEscapeToBasculegion:hasVerifiedMatchupAnswer({...record,
                  variants:[{...record.variants[0],ability:'かげふみ'}],
                  answers:[{...record.answers[0],pokemon:'イダイトウ♂'}],
                  leadChecks:[{...record.leadChecks[0],response:'switch',
                    switchTo:'イダイトウ♂'}]},
                  'ドヒドイデ',['カバルドン','イダイトウ♂','ミミッキュ'],'カバルドン'),
                // A "switch" to the active Pokemon is not a legal action.
                selfSwitch:check({...record,leadChecks:[{...record.leadChecks[0],
                  response:'switch',switchTo:'カバルドン'}]}),
                missingBranch:check({...record,variants:[...record.variants,
                  {...record.variants[0],id:'mega'}]}),
                badSwitch:check({...record,leadChecks:[{...record.leadChecks[0],
                  response:'switch',switchTo:'アシレーヌ'}]}),
                missingSpeedReview:check({...record,variants:[{
                  ...record.variants[0],speedRangeReviewed:false}]}),
                reversedSpeedRange:check({...record,variants:[{
                  ...record.variants[0],speedMin:120,speedMax:95}]}),
                missingMoveReview:check({...record,variants:[{
                  ...record.variants[0],moveCoverageReviewed:false}]}),
                emptyMoves:check({...record,variants:[{
                  ...record.variants[0],moves:[]}]}),
                missingItemReview:check({...record,variants:[{
                  ...record.variants[0],itemCoverageReviewed:false}]}),
                emptyItems:check({...record,variants:[{
                  ...record.variants[0],items:[]}]}),
                unlistedPriority:check({...record,variants:[{
                  ...record.variants[0],priorityMoves:['しんそく']}]}),
                badCitation:check({...record,answers:[{...record.answers[0],source:''}]}),
                unrelatedLeadAnswer:check({...record,answers:[{
                  ...record.answers[0],pokemon:'ミミッキュ'}]}),
                missingVariantAnswer:check({...record,variants:[
                  ...record.variants,{...record.variants[0],id:'otherAbility'}]}),
                missingLeadReason:check({...record,leadChecks:[{
                  ...record.leadChecks[0],reason:''}]}),
                missingMegaBranch:hasVerifiedMatchupAnswer(
                  {...record,form:'リザードン',variants:[{
                    ...record.variants[0],form:'リザードン'}]},
                  'リザードン',team,'カバルドン'),
                charizardBranches:requiredMatchupForms('リザードン'),
                alolanRaichuBranches:requiredMatchupForms('アローラライチュウ'),
                maleMeowsticBranches:requiredMatchupForms('ニャオニクス(オス)'),
                eternalFloetteBranches:requiredMatchupForms('フラエッテ(えいえんのはな)'),
                ordinaryFloetteBranches:requiredMatchupForms('フラエッテ'),
                megaFloetteBranches:requiredMatchupForms('メガフラエッテ')
              };
            }""")
            assert gate == {'complete': True, 'oldNameOnly': False, 'wrongForm': False,
                            'wrongLead': False, 'unsafe': False, 'conflictingLead': False,
                            'duplicateLead': False, 'shadowTagTrapped': False,
                            'shadowTagGhostCanSwitch': True,
                            'shadowTagBasculegionCanSwitch': True,
                            'shadowTagCannotEscapeToBasculegion': False,
                            'selfSwitch': False, 'missingBranch': False,
                            'badSwitch': False, 'badCitation': False,
                            'missingSpeedReview': False, 'reversedSpeedRange': False,
                            'missingMoveReview': False, 'emptyMoves': False,
                            'missingItemReview': False, 'emptyItems': False,
                            'unlistedPriority': False,
                            'unrelatedLeadAnswer': False, 'missingVariantAnswer': False,
                            'missingLeadReason': False, 'missingMegaBranch': False,
                            'charizardBranches': ['リザードン','メガリザードンX','メガリザードンY'],
                            'alolanRaichuBranches': ['アローラライチュウ'],
                            'maleMeowsticBranches': ['ニャオニクス(オス)','メガニャオニクス(オス)'],
                            'eternalFloetteBranches': ['フラエッテ(えいえんのはな)','メガフラエッテ'],
                            'ordinaryFloetteBranches': ['フラエッテ'],
                            'megaFloetteBranches': ['メガフラエッテ']}, gate
            # Synthetic evidence ONLY: a reviewed Mega or base+all Mega branches
            # must not be vetoed by an unconditional Mega/critical/terrain flag.
            # Missing a single form, a reviewed lead or a selected team answer
            # must still fail closed. No synthetic record is persisted to the app.
            branch_gate = page.evaluate("""() => {
              const cited={source:'https://example.org/synthetic-fixture',updated:'2026-10-29'};
              const team=['カバルドン','ミミッキュ','メガルカリオZ'];
              const lead='カバルドン';
              const mk=form=>{
                const forms=requiredMatchupForms(form);
                const variants=forms.map((f,i)=>({...cited,id:'v'+i,form:f,
                  reviewed:true,ability:'fixture-only',speedBase:100,
                  speedRangeReviewed:true,speedMin:50,speedMax:150,
                  moveCoverageReviewed:true,moves:['fixture-move'],
                  itemCoverageReviewed:true,items:['fixture-item'],
                  priorityMoves:[]}));
                return {...cited,form,reviewed:true,formReviewed:true,
                  branchScope:'all-known',variants,
                  answers:variants.map(v=>({...cited,variant:v.id,
                    pokemon:lead,reason:'synthetic fixture',reviewed:true})),
                  leadChecks:variants.map(v=>({...cited,variant:v.id,
                    lead,response:'stay',reason:'synthetic fixture',reviewed:true}))};
              };
              const evidence={
                'リザードン':mk('リザードン'),
                'メガリザードンY':mk('メガリザードンY'),
                'イエッサン(メス)':mk('イエッサン(メス)'),
                'イエッサン(オス)':mk('イエッサン(オス)')
              };
              const names=['リザードン','メガリザードンY','イエッサン(メス)','イエッサン(オス)'];
              const compact=x=>({missing:x.missing,megaForms:x.megaForms,
                megaBases:x.megaBases});
              const full=unverifiedMatchupBranches(names,team,lead,evidence);
              const none=unverifiedMatchupBranches(names,team,lead,{});
              const incomplete={...evidence,'リザードン':{
                ...evidence['リザードン'],
                variants:evidence['リザードン'].variants.slice(0,2)}};
              const partial=unverifiedMatchupBranches(names,team,lead,incomplete);
              const wrongLead=unverifiedMatchupBranches(names,team,'ミミッキュ',evidence);
              const megaOnly=unverifiedMatchupBranches(['メガリザードンY'],
                team,lead,{'メガリザードンY':evidence['メガリザードンY']});
              return {full:compact(full),none:compact(none),partial:compact(partial),
                wrongLead:compact(wrongLead),megaOnly:compact(megaOnly),
                fullCritical:full.missing.some(n=>n==='リザードン'),
                fullTerrain:full.missing.some(n=>n==='イエッサン(メス)'),
                missingCritical:none.missing.includes('リザードン'),
                missingTerrain:none.missing.includes('イエッサン(メス)')};
            }""")
            assert branch_gate == {
                'full': {'missing': [], 'megaForms': [], 'megaBases': []},
                'none': {'missing': ['リザードン','メガリザードンY','イエッサン(メス)','イエッサン(オス)'],
                         'megaForms': ['メガリザードンY'],
                         'megaBases': ['リザードン']},
                'partial': {'missing': ['リザードン'],
                            'megaForms': [], 'megaBases': ['リザードン']},
                'wrongLead': {'missing': ['リザードン','メガリザードンY','イエッサン(メス)','イエッサン(オス)'],
                              'megaForms': ['メガリザードンY'],
                              'megaBases': ['リザードン']},
                'megaOnly': {'missing': [], 'megaForms': [], 'megaBases': []},
                'fullCritical': False, 'fullTerrain': False,
                'missingCritical': True, 'missingTerrain': True
            }, branch_gate
            # Regional variants must not inherit another form's Mega branch.
            # This is a threat-warning correctness check, NOT matchup clearance.
            regional_case = ['アローラライチュウ','ミミッキュ','ドドゲザン',
                             'ペリッパー','アシレーヌ','サーフゴー']
            for i, name in enumerate(regional_case):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#analyze').click()
            assert page.locator('#result .abstention-banner').count() == 1
            assert page.locator('#result .mega-base-unverified').count() == 0
            assert page.locator('#result .mega-uncertainty').count() == 0
            assert page.evaluate("() => megaCandidatesFor(['アローラライチュウ']).length") == 0
            assert page.evaluate("() => megaCandidatesFor(['ライチュウ']).length") == 1
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
            assert '全件照合2026-10-29成功' in page.locator('#result .evidence-summary').inner_text()

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

            # Additional high-risk Mega profiles show source-dated facts, not
            # an unsafe recommended lead; normal forms keep both branches open.
            for threat,base,ability,speed,source in (
                ('メガリザードンY','リザードン','ひでり','100','554808'),
                ('メガゲンガー','ゲンガー','かげふみ','130','554816'),
            ):
                page.locator('#foe0').fill(threat)
                page.locator('#analyze').click()
                card = page.locator('#result .extra-sourced-intel')
                assert card.count() == 1
                assert all(x in card.inner_text() for x in (ability,speed,'未検証'))
                assert card.locator('a[href*="'+source+'"]').count() == 1
                assert page.locator('#result .hero').count() == 0
                page.locator('#foe0').fill(base)
                page.locator('#analyze').click()
                assert 'メガシンカ確定ではありません' in page.locator('#result .extra-sourced-intel').inner_text()
                assert page.locator('#result .hero').count() == 0

            # Eternal Flower Floette is the only Floette form with this Mega
            # branch. Preserve the distinction in warnings and evidence gating.
            for i, name in enumerate(('フラエッテ(えいえんのはな)', 'アシレーヌ',
                                      'ドドゲザン', 'サーフゴー', 'ミミッキュ',
                                      'カバルドン')):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#analyze').click()
            assert page.locator('#result .mega-base-unverified').count() == 1
            assert 'フラエッテ(えいえんのはな)' in page.locator('#result .mega-base-unverified').inner_text()
            card = page.locator('#result .extra-sourced-intel')
            assert card.count() == 1
            assert 'フェアリーオーラ' in card.inner_text()
            assert '102' in card.inner_text()
            assert card.locator('a[href*="553325"]').count() == 1
            assert page.locator('#result .hero').count() == 0
            page.locator('#foe0').fill('メガフラエッテ')
            page.locator('#analyze').click()
            assert page.locator('#result .mega-form-unverified').count() == 1
            assert page.locator('#result .extra-sourced-intel').count() == 1
            assert page.locator('#result .hero').count() == 0
            page.locator('#foe0').fill('フラエッテ')
            page.locator('#analyze').click()
            assert page.locator('#result .mega-base-unverified').count() == 0
            assert page.locator('#result .extra-sourced-intel').count() == 0
            assert page.locator('#result .hero').count() == 0

            # Source-backed *conditional* matchup risks must be visible for
            # both explicit Mega forms and a possible Mega branch of a base
            # form. They must NEVER unlock a three-pick or lead recommendation.
            for opponent, base, own, source, warning in (
                ('メガグソクムシャ', 'グソクムシャ', 'カバルドン', '575652', 'つるぎのまい'),
                ('メガリザードンY', 'リザードン', 'カバルドン', '554808', 'ソーラービーム'),
                ('メガゲンガー', 'ゲンガー', 'カバルドン', '555161', 'かげふみ'),
            ):
                for i, name in enumerate((opponent, 'サーフゴー', 'ガブリアス',
                                          'ドドゲザン', 'ペリッパー', 'アシレーヌ')):
                    page.locator(f'#foe{i}').fill(name)
                page.locator('#analyze').click()
                risk = page.locator('#result .reviewed-pair-risks')
                assert risk.count() == 1
                assert risk.locator('details').get_attribute('open') is None
                risk.locator('summary').click()
                assert risk.locator('details').get_attribute('open') is not None
                assert all(x in risk.inner_text() for x in (own, opponent, warning, '未検証'))
                assert risk.locator('a[href*="'+source+'"]').count() >= 1
                # Reviewed M-7 observations are form-specific warning context,
                # not proof of an advantageous lead or a complete move set.
                observed = {
                    'メガグソクムシャ': ('54〜101', 'ふいうち 80.2%', 'であいがしら', 'アクアジェット', '優先度+2', '5位'),
                    'メガリザードンY': ('108〜167', 'ソーラービーム 65.2%', '先制技候補', '未確認', '6位'),
                    'メガゲンガー': ('135〜200', 'シャドーボール 81.4%', 'かげふみ', '未確認', '23位'),
                }[opponent]
                assert all(x in risk.inner_text() for x in observed), (opponent, risk.inner_text())
                assert '全型の上下限ではありません' in risk.inner_text()
                assert 'メガ型への採用を断定しません' in risk.inner_text()
                assert '2026-10-28' in risk.inner_text()
                assert '出典付き条件付き対面注意 1件' in page.locator('#result .evidence-summary').inner_text()
                assert '検証済み対面 0/6匹' in page.locator('#result .evidence-summary').inner_text()
                assert page.locator('#result .hero').count() == 0
                page.locator('#foe0').fill(base)
                page.locator('#analyze').click()
                assert page.locator('#result .reviewed-pair-risks').count() == 1
                assert page.locator('#result .hero').count() == 0
            page.locator('#foe0').fill('エースバーン')
            page.locator('#analyze').click()
            assert page.locator('#result .reviewed-pair-risks').count() == 0
            # Badly sourced or structurally corrupt data must not appear
            # as reviewed risks, nor be promoted to verified matchups.
            risk_gate = page.evaluate("""() => {
              const p=reviewedPairRisks[0];
              return [
                isReviewedPairRisk(p),
                isReviewedPairRisk({...p,statsUpdated:'unknown'}),
                isReviewedPairRisk({...p,usageRank:0}),
                isReviewedPairRisk({...p,speedExampleMin:200,speedExampleMax:101}),
                isReviewedPairRisk({...p,observedMoves:[{move:'ふいうち',percent:120}]}),
                isReviewedPairRisk({...p,priorityMoves:[{move:'ふいうち',priority:0,condition:'always'}]}),
                isReviewedPairRisk({...p,scope:'safe-lead'}),
                Object.keys(verifiedMatchupEvidence).length
              ];
            }""")
            assert risk_gate == [True, False, False, False, False, False, False, 0], risk_gate

            # Two source-reviewed NEGATIVE actions (Shadow Tag / Ground immunity), not safe
            # matchup. It must be shown for explicit Mega and possible Mega
            # branches, but never unlock the team/lead recommendation.
            unsafe_gate = page.evaluate("""() => {
              const e=verifiedUnsafeActionEvidence[0];
              return {
                count:verifiedUnsafeActionEvidence.length,
                valid:isVerifiedUnsafeActionEvidence(e),
                wrongSource:isVerifiedUnsafeActionEvidence({...e,source:''}),
                wrongAbility:isVerifiedUnsafeActionEvidence({...e,ability:'ふゆう'}),
                ghostLead:isVerifiedUnsafeActionEvidence({...e,
                  ownLead:'ミミッキュ',heldItem:'いのちのたま'}),
                wrongItem:isVerifiedUnsafeActionEvidence({...e,heldItem:'オボンのみ'}),
                promotedToSafe:isVerifiedUnsafeActionEvidence({...e,scope:'safe-lead'}),
                verifiedSafeCount:Object.keys(verifiedMatchupEvidence).length
              };
            }""")
            assert unsafe_gate == {'count':55,'valid':True,'wrongSource':False,
                'wrongAbility':False,'ghostLead':False,'wrongItem':False,
                'promotedToSafe':False,'verifiedSafeCount':0}, unsafe_gate
            # Reviewed interaction facts: 5 terrain-vs-priority moves and 4
            # Mega Golisopod First Impression (+2) vs roster priority (+1).
            # They must NEVER count as safe matchup answers.
            conditional_gate=page.evaluate("""() => {
              const e=reviewedConditionalLeadInteractions;
              return {
                total:e.length,
                valid:e.every(isReviewedConditionalLeadInteraction),
                terrain:e.filter(x=>x.mechanic==='psychic-terrain').length,
                priority:e.filter(x=>x.mechanic==='priority-order').length,
                ties:e.filter(x=>x.mechanic==='priority-tie').length,
                wrongSource:isReviewedConditionalLeadInteraction({...e[0],source:''}),
                wrongFemaleSource:isReviewedConditionalLeadInteraction({...e[0],femaleSource:''}),
                wrongUpdate:isReviewedConditionalLeadInteraction({...e[0],sourceUpdated:'未確認'}),
                wrongMove:isReviewedConditionalLeadInteraction({...e[0],move:'じしん'}),
                wrongPriority:isReviewedConditionalLeadInteraction({...e[5],opponentPriority:1}),
                promoted:isReviewedConditionalLeadInteraction({...e[0],scope:'safe-lead'}),
                safe:Object.keys(verifiedMatchupEvidence).length
              };
            }""")
            assert conditional_gate == {'total':14,'valid':True,'terrain':5,'ties':5,
                'priority':4,'wrongSource':False,'wrongFemaleSource':False,'wrongUpdate':False,'wrongMove':False,
                'wrongPriority':False,'promoted':False,'safe':0}, conditional_gate
            conditional_names=['イエッサン','グソクムシャ','ミミッキュ',
                               'サーフゴー','アシレーヌ','ガブリアス']
            for i, name in enumerate(conditional_names):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#analyze').click()
            assert '公式M-C入力網羅率 100%' in page.locator('#result .evidence-summary').inner_text()
            assert '検証済み対面率 0%' in page.locator('#result .evidence-summary').inner_text()
            assert '条件付き技相互作用 14件' in page.locator('#result .conditional-interactions').inner_text()
            assert page.locator('#result .conditional-interactions .line').count() == 14
            assert page.locator('#result .conditional-interactions details').get_attribute('open') is None
            page.locator('#result .conditional-interactions summary').click()
            assert page.locator('#result .conditional-interactions details').get_attribute('open') is not None
            assert '検証済み対面 0/6匹' in page.locator('#result .evidence-summary').inner_text()
            assert page.locator('#result .hero').count() == 0
            page.locator('#foe0').fill('イエッサン(メス)')
            page.locator('#foe1').fill('メガリザードンY')
            page.locator('#analyze').click()
            assert page.locator('#result .conditional-interactions .line').count() == 5
            page.locator('#foe0').fill('メガグソクムシャ')
            page.locator('#analyze').click()
            assert page.locator('#result .conditional-interactions .line').count() == 9
            page.locator('#foe0').fill('メガゲンガー')
            page.locator('#analyze').click()
            assert page.locator('#result .conditional-interactions').count() == 0

            # Reviewed M-C and historical Mega sample sets are reference data,
            # never verified opponent adoption or an unlocked safe lead.
            sample_profiles=page.evaluate("""() => reviewedOpponentProfiles.map(p=>({
              form:p.form,regulation:p.regulation,source:p.source,
              item:p.item,ability:p.ability,moves:p.moves,
              speed:[p.speedMin,p.speedMax],sample:p.sampleSpeed
            }))""")
            assert len(sample_profiles)==14
            assert sample_profiles[0]['form']=='メガグソクムシャ'
            assert sample_profiles[0]['regulation']=='M-C'
            assert sample_profiles[0]['speed']==[54,101]
            assert sample_profiles[0]['sample']==60
            assert sample_profiles[0]['moves']==['ビルドアップ','きゅうけつ','アイアンヘッド','ふいうち']
            assert sample_profiles[1]['regulation'].startswith('M-A/M-B')
            assert sample_profiles[1]['sample']==200
            assert sample_profiles[2]['regulation'].startswith('M-A/M-B')
            assert sample_profiles[2]['sample']==120
            assert all(p['source'].startswith('https://gamewith.jp/pokemon-champions/') for p in sample_profiles)
            assert page.evaluate("""() => [
              referenceSpeedComparison(201,reviewedOpponentProfiles[1]),
              referenceSpeedComparison(67,reviewedOpponentProfiles[2]),
              referenceSpeedComparison(67,reviewedOpponentProfiles[0])
            ]""")==[
              '掲載最速例より速い（差+1）',
              '掲載最遅例より遅い（差-41）',
              '掲載例の範囲内（型次第）'
            ]
            profile_names=['グソクムシャ','ゲンガー','リザードン',
                           'アシレーヌ','ガブリアス','カバルドン']
            for i,name in enumerate(profile_names):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#analyze').click()
            assert page.locator('#result .reviewed-opponent-profile').count()==5
            page.locator('#result .reviewed-opponent-profiles summary').click()
            assert page.locator('#result .speed-comparison').count()==36
            assert '出典付き主要型参考例 5件' in page.locator('#result .evidence-summary').inner_text()
            assert 'M-A/M-B（過去の参考型）' in page.locator('#result .reviewed-opponent-profiles').inner_text()
            assert page.locator('#result .hero').count()==0
            assert '検証済み対面 0/6匹' in page.locator('#result .evidence-summary').inner_text()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2')
            page.locator('#foe2').fill('メガリザードンX')
            page.locator('#analyze').click()
            assert page.locator('#result .reviewed-opponent-profile').count()==4
            assert 'メガリザードンY' not in page.locator('#result .reviewed-opponent-profiles').inner_text()
            page.locator('#foe2').fill('メガリザードンY')
            page.locator('#analyze').click()
            assert page.locator('#result .reviewed-opponent-profile').count()==4
            assert page.locator('#result .hero').count()==0

            unsafe_names=['メガゲンガー','ミミッキュ','サーフゴー',
                          'アシレーヌ','ニンフィア','カバルドン']
            for i, name in enumerate(unsafe_names):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#analyze').click()
            assert page.locator('#result .verified-unsafe-action').count() == 1
            assert '通常交代不可' in page.locator('#result .verified-unsafe-action').inner_text()
            assert '2026-10-27' in page.locator('#result .verified-unsafe-action').inner_text()
            assert page.locator('#result .hero').count() == 0
            page.locator('#foe0').fill('ゲンガー')
            page.locator('#analyze').click()
            assert page.locator('#result .verified-unsafe-action').count() == 1
            assert page.locator('#result .hero').count() == 0
            page.locator('#foe0').fill('メガグソクムシャ')
            page.locator('#analyze').click()
            # Other slots still contain Mimikyu and Gholdengo, both Ghost.
            assert page.locator('#result .verified-unsafe-action .line').count() == 6
            assert page.locator('#result .hero').count() == 0

            # Ghost immunities: exact moves, items and sources, never a safe lead.
            immune_gate=page.evaluate("""() => {
              return verifiedUnsafeActionEvidence.slice(4,7).map(e=>({
                lead:e.ownLead,move:e.action,valid:isVerifiedUnsafeActionEvidence(e),
                wrongMove:isVerifiedUnsafeActionEvidence({...e,action:'じしん'}),
                wrongChart:isVerifiedUnsafeActionEvidence({...e,mechanicSource:''}),
                wrongSource:isVerifiedUnsafeActionEvidence({...e,source:''}),
                wrongItem:isVerifiedUnsafeActionEvidence({...e,heldItem:'オボンのみ'})
              }));
            }""")
            assert [(x['lead'],x['move']) for x in immune_gate] == [
              ('メガカイリュー','しんそく'),
              ('メガルカリオZ','しんくうは'),
              ('ギルガルド','インファイト')], immune_gate
            assert all(x['valid'] and not x['wrongMove'] and not x['wrongChart']
                       and not x['wrongSource'] and not x['wrongItem'] for x in immune_gate)
            page.locator('#foe0').fill('メガゲンガー')
            page.locator('#analyze').click()
            ghost_warning=page.locator('#result .verified-unsafe-action')
            assert ghost_warning.locator('.line').count() == 12
            for move in ('しんそく','しんくうは','インファイト'):
                assert move+'無効（条件付き）' in ghost_warning.inner_text()
            assert page.locator('#result .hero').count() == 0

            # Twelve new source-reviewed Ghost immunities (4 species x 3
            # roster moves), all strictly conditional and NEVER safe answers.
            ghost_batch=page.evaluate("""() => verifiedUnsafeActionEvidence.slice(7,22).map(e=>({
              form:e.form,move:e.action,valid:isVerifiedUnsafeActionEvidence(e),
              wrongType:isVerifiedUnsafeActionEvidence({...e,ability:'かげふみ'}),
              wrongMoveSource:isVerifiedUnsafeActionEvidence({...e,moveSource:''}),
              wrongDate:isVerifiedUnsafeActionEvidence({...e,sourceUpdated:'未確認'}),
              wrongForm:isVerifiedUnsafeActionEvidence({...e,form:'メガグソクムシャ'}),
              wrongScope:isVerifiedUnsafeActionEvidence({...e,scope:'safe-lead'})
            }))""")
            assert len(ghost_batch)==15, ghost_batch
            assert set(x['form'] for x in ghost_batch)=={'ゲンガー','ミミッキュ','サーフゴー','ドラパルト','メガアブソルZ'}
            assert all(x['valid'] and not x['wrongType'] and not x['wrongMoveSource']
                and not x['wrongDate'] and not x['wrongForm'] and not x['wrongScope']
                for x in ghost_batch)
            # Remove the other Ghost opponents so each case has an exact count.
            page.locator('#foe1').fill('ドドゲザン')
            page.locator('#foe2').fill('エースバーン')
            for opponent, expected in [('ミミッキュ',3),('サーフゴー',3),
                                       ('ドラパルト',3),('ゲンガー',9)]:
                page.locator('#foe0').fill(opponent)
                page.locator('#analyze').click()
                assert page.locator('#result .verified-unsafe-action .line').count()==expected
                assert page.locator('#result .hero').count()==0
                assert page.locator('#result .risk-matrix .matrix-foe').count()==6
                assert page.locator('#result .risk-matrix .matrix-cell').count()==36
                assert page.locator('#result .risk-matrix details').get_attribute('open') is None
                assert '未検証（安全性不明）' in page.locator('#result .risk-matrix').text_content()
                assert 'しんそく' in page.locator('#result .risk-matrix').text_content()
                assert page.evaluate('() => document.documentElement.scrollWidth <= innerWidth + 1')
            page.locator('#result .risk-matrix summary').click()
            assert page.locator('#result .risk-matrix details').get_attribute('open') is not None
            assert page.locator('#result .hero').count()==0

            tie_gate=page.evaluate("""() => {
              return reviewedConditionalLeadInteractions.slice(9).map(e=>({
                own:e.own,move:e.move,opponent:e.opponentMove,
                valid:isReviewedConditionalLeadInteraction(e),
                wrongOpponent:isReviewedConditionalLeadInteraction({...e,opponentMove:'アクアジェット'}),
                wrongPriority:isReviewedConditionalLeadInteraction({...e,opponentPriority:0}),
                wrongSource:isReviewedConditionalLeadInteraction({...e,source:''})
              }));
            }""")
            assert len(tie_gate)==5 and all(x['valid'] and not x['wrongOpponent']
                and not x['wrongPriority'] and not x['wrongSource'] for x in tie_gate)
            assert tie_gate[-1]['move']=='しんそく' and tie_gate[-1]['opponent']=='であいがしら'
            page.locator('#foe0').fill('メガグソクムシャ')
            page.locator('#analyze').click()
            assert page.locator('#result .conditional-interactions .line').count() == 9
            page.locator('#result .conditional-interactions summary').click()
            assert '素早さ等によって行動順が変わる' in page.locator('#result .conditional-interactions').inner_text()
            assert page.locator('#result .hero').count() == 0

            # Both additional non-Ghost leads must have exact, cited vetoes.
            shadow_branches=page.evaluate("""() => {
              return verifiedUnsafeActionEvidence.slice(1,3).map(e=>({
                lead:e.ownLead,valid:isVerifiedUnsafeActionEvidence(e),
                wrongItem:isVerifiedUnsafeActionEvidence({...e,heldItem:'オボンのみ'}),
                ghostLead:isVerifiedUnsafeActionEvidence({...e,ownLead:'ミミッキュ',heldItem:'いのちのたま'}),
                wrongAbility:isVerifiedUnsafeActionEvidence({...e,ability:'ふゆう'})
              }));
            }""")
            assert [x['lead'] for x in shadow_branches] == ['メガルカリオZ','メガカイリュー']
            assert all(x['valid'] and not x['wrongItem'] and not x['ghostLead'] and not x['wrongAbility'] for x in shadow_branches)

            # The second independently sourced negative action is a move-specific
            # immunity: Hippowdon's Earthquake vs Flying-type Mega Charizard Y.
            # It must not be confused with a safe lead or guaranteed victory.
            ground_gate = page.evaluate("""() => {
              const e=verifiedUnsafeActionEvidence[3];
              return {
                valid:isVerifiedUnsafeActionEvidence(e),
                wrongSource:isVerifiedUnsafeActionEvidence({...e,source:''}),
                wrongMoveSource:isVerifiedUnsafeActionEvidence({...e,moveSource:''}),
                wrongChart:isVerifiedUnsafeActionEvidence({...e,mechanicSource:''}),
                wrongMove:isVerifiedUnsafeActionEvidence({...e,action:'ステルスロック'}),
                wrongAbility:isVerifiedUnsafeActionEvidence({...e,ability:'もうか'}),
                wrongItem:isVerifiedUnsafeActionEvidence({...e,heldItem:'オボンのみ'}),
                wrongForm:isVerifiedUnsafeActionEvidence({...e,form:'メガリザードンX'}),
                wrongScope:isVerifiedUnsafeActionEvidence({...e,scope:'safe-lead'}),
                safeCount:Object.keys(verifiedMatchupEvidence).length
              };
            }""")
            assert ground_gate == {'valid':True,'wrongSource':False,
                'wrongMoveSource':False,'wrongChart':False,'wrongMove':False,
                'wrongAbility':False,'wrongItem':False,'wrongForm':False,
                'wrongScope':False,'safeCount':0}, ground_gate
            page.locator('#foe0').fill('メガリザードンY')
            page.locator('#analyze').click()
            warning=page.locator('#result .verified-unsafe-action')
            assert warning.count() == 1
            assert 'じしん無効（条件付き）' in warning.inner_text()
            assert '2026-10-28' in warning.inner_text()
            assert warning.locator('a[href*="554282"]').count() == 1
            assert warning.locator('a[href*="546446"]').count() == 1
            assert '検証済み危険行動 1件' in page.locator('#result .evidence-summary').inner_text()
            assert '検証済み対面 0/6匹' in page.locator('#result .evidence-summary').inner_text()
            assert page.locator('#result .hero').count() == 0
            page.locator('#foe0').fill('リザードン')
            page.locator('#analyze').click()
            assert 'じしん無効（条件付き）' in page.locator('#result .verified-unsafe-action').inner_text()
            page.locator('#foe0').fill('メガリザードンX')
            page.locator('#analyze').click()
            assert page.locator('#result .verified-unsafe-action').count() == 0
            page.locator('#foe0').fill('メガリザードンY')
            page.locator('#foe1').fill('メガゲンガー')
            page.locator('#analyze').click()
            assert '検証済み危険行動 7件' in page.locator('#result .evidence-summary').inner_text()
            assert page.locator('#result .verified-unsafe-action .line').count() == 7
            assert page.locator('#result .hero').count() == 0

            # Four new current M-C profiles (separate from verified safe matchups).
            current_mc=page.evaluate("""() => reviewedOpponentProfiles.slice(3,7).map(p=>({
              form:p.form,regulation:p.regulation,source:p.source,updated:p.updated,
              item:p.item,ability:p.ability,speed:[p.speedMin,p.speedMax],
              moves:p.moves,priority:p.priority
            }))""")
            assert [p['form'] for p in current_mc]==[
                'メガボーマンダ','メガガブリアスZ','メガルカリオZ','メガアブソルZ']
            assert [p['speed'] for p in current_mc]==[
                [126,189],[153,223],[153,223],[153,223]]
            assert all(p['regulation']=='M-C' and p['source'].startswith(
                'https://gamewith.jp/pokemon-champions/') and
                p['updated'].startswith('2026-10-') for p in current_mc)
            assert current_mc[1]['ability']=='ふゆう'
            assert current_mc[2]['ability']=='はどうのぼうご'
            assert current_mc[3]['ability']=='きれあじ'
            assert page.evaluate("() => Object.keys(verifiedMatchupEvidence).length")==0
            # Three new M-C sources, including the actual Shell Smash loss
            # condition, are reference profiles rather than safe matchups.
            expanded=page.evaluate("""() => reviewedOpponentProfiles.slice(7,10).map(p=>({
              form:p.form,source:p.source,updated:p.updated,usageRank:p.usageRank,
              item:p.item,ability:p.ability,moves:p.moves,
              speed:[p.speedMin,p.speedMax],boost:boostedSpeedRange(p),
              priority:p.priority,valid:isReviewedOpponentProfile(p)
            }))""")
            assert [x['form'] for x in expanded]==[
                'メガカメックス','メガセグレイブ','メガゲッコウガ']
            assert [x['speed'] for x in expanded]==[
                [88,143],[96,152],[145,213]]
            assert [x['boost'] for x in expanded]==[
                [176,286],[144,228],None]
            assert [x['usageRank'] for x in expanded]==[34,13,28]
            assert all(x['valid'] and x['source'].startswith(
                'https://gamewith.jp/pokemon-champions/') and
                x['updated']=='2026-10-28' for x in expanded)
            assert expanded[0]['item']=='カメックスナイト'
            assert expanded[0]['ability']=='メガランチャー'
            assert 'からをやぶる' in expanded[0]['moves']
            assert expanded[1]['ability']=='ねつこうかん'
            assert 'こおりのつぶて' in expanded[1]['moves']
            assert expanded[2]['ability']=='へんげんじざい'
            assert 'みずしゅりけん+1' in expanded[2]['priority']
            bad_profile=page.evaluate("""() => {
              const p=reviewedOpponentProfiles[7];
              return {
                source:isReviewedOpponentProfile({...p,source:''}),
                date:isReviewedOpponentProfile({...p,updated:'unknown'}),
                speed:isReviewedOpponentProfile({...p,speedMin:300,speedMax:143}),
                boost:isReviewedOpponentProfile({...p,boostedSpeedStage:3}),
                move:isReviewedOpponentProfile({...p,boostedSpeedMove:'未収録技'}),
                invalidBoost:boostedSpeedRange({...p,boostedSpeedStage:3}),
                reviewedCount:reviewedOpponentProfiles.filter(isReviewedOpponentProfile).length,
                verifiedSafe:Object.keys(verifiedMatchupEvidence).length
              };
            }""")
            assert bad_profile=={
                'source':False,'date':False,'speed':False,'boost':False,
                'move':False,'invalidBoost':None,'reviewedCount':14,
                'verifiedSafe':0}, bad_profile
            for i,name in enumerate(['カメックス','セグレイブ','ゲッコウガ',
                                     'アシレーヌ','ガブリアス','ペリッパー']):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#analyze').click()
            assert page.locator('#result .hero').count()==0
            assert page.locator('#result .reviewed-opponent-profile').count()==4
            assert '検証済み対面 0/6匹' in page.locator('#result .evidence-summary').inner_text()
            page.locator('#result .reviewed-opponent-profiles summary').click()
            assert page.locator('#result .boosted-speed-risk').count()==2
            assert page.locator('#result .boosted-speed-comparison').count()==12
            boost_text=page.locator('#result .reviewed-opponent-profiles').inner_text()
            assert 'からをやぶる成功時のみ素早さ+2段階：176〜286' in boost_text
            assert 'りゅうのまい成功時のみ素早さ+1段階：144〜228' in boost_text
            assert 'みずしゅりけん+1' in boost_text
            page.locator('#result .risk-matrix summary').click()
            matrix=page.locator('#result .risk-matrix')
            assert matrix.locator('.matrix-cell').count()==36
            assert 'からをやぶる成功後の素早さ176〜286' in matrix.inner_text()
            assert 'りゅうのまい成功後の素早さ144〜228' in matrix.inner_text()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2')
            # Exact Mega and pre-Mega branches both show a conditional boost.
            page.locator('#foe0').fill('メガカメックス')
            page.locator('#analyze').click()
            # The independent Mega Baxcalibur branch remains present.
            assert page.locator('#result .boosted-speed-risk').count()==2
            assert page.locator('#result .reviewed-opponent-profile').count()==4
            assert page.locator('#result .hero').count()==0

            # Five exact negative move interactions; normal forms remain
            # uncertain until Mega evolution, and sibling Mega forms are distinct.
            new_unsafe=page.evaluate("""() => verifiedUnsafeActionEvidence.slice(19,24).map(e=>({
              form:e.form,lead:e.ownLead,move:e.action,
              valid:isVerifiedUnsafeActionEvidence(e),
              wrongSource:isVerifiedUnsafeActionEvidence({...e,source:''}),
              wrongItem:isVerifiedUnsafeActionEvidence({...e,heldItem:'オボンのみ'}),
              wrongAbility:isVerifiedUnsafeActionEvidence({...e,ability:'かげふみ'}),
              wrongMove:isVerifiedUnsafeActionEvidence({...e,action:'ステルスロック'}),
              wrongScope:isVerifiedUnsafeActionEvidence({...e,scope:'safe-lead'})
            }))""")
            assert len(new_unsafe)==5, new_unsafe
            assert set(x['form'] for x in new_unsafe)=={
                'メガアブソルZ','メガボーマンダ','メガガブリアスZ'}
            assert all(x['valid'] and not x['wrongSource'] and
                not x['wrongItem'] and not x['wrongAbility'] and
                not x['wrongMove'] and not x['wrongScope'] for x in new_unsafe)
            for target,expected in [
                ('メガボーマンダ',1),('メガガブリアスZ',1),
                ('メガアブソルZ',3)]:
                for i,name in enumerate([target,'アシレーヌ','ドドゲザン',
                                           'ニンフィア','カバルドン','ペリッパー']):
                    page.locator(f'#foe{i}').fill(name)
                page.locator('#analyze').click()
                assert page.locator('#result .verified-unsafe-action .line').count()==expected
                assert page.locator('#result .hero').count()==0
                assert '検証済み対面 0/6匹' in page.locator('#result .evidence-summary').inner_text()
            for base,mega,expected in [
                ('ボーマンダ','メガボーマンダ','じしん'),
                ('ガブリアス','メガガブリアスZ','じしん'),
                ('アブソル','メガアブソルZ','しんそく')]:
                page.locator('#foe0').fill(base)
                page.locator('#analyze').click()
                assert expected+'無効（条件付き）' in page.locator('#result .verified-unsafe-action').inner_text()
                assert mega in page.locator('#result .verified-unsafe-action').inner_text()
            # A different Mega branch must not inherit the Ground immunity.
            page.locator('#foe0').fill('メガガブリアス')
            page.locator('#analyze').click()
            assert page.locator('#result .verified-unsafe-action').count()==0
            page.locator('#foe0').fill('メガリザードンX')
            page.locator('#analyze').click()
            assert page.locator('#result .verified-unsafe-action').count()==0
            assert page.evaluate('() => document.documentElement.scrollWidth <= innerWidth + 2')

            # 2026-10-29: nine additional exact Ghost forms (27 negative moves)
            # plus two Magic Bounce Mega forms x two Hippo setup moves.
            # Neither batch counts as a safe matchup or unlocks recommendations.
            extra_negative=page.evaluate("""() => {
              const ghost=verifiedUnsafeActionEvidence.filter(e=>
                additionalGhostImmunityTargets.some(t=>t.form===e.form) && e.ability==='type-only');
              const bounce=verifiedUnsafeActionEvidence.filter(e=>
                e.ability==='マジックミラー');
              return {
                ghostForms:additionalGhostImmunityTargets.length,
                ghostCount:ghost.length,
                bounceCount:bounce.length,
                allValid:[...ghost,...bounce].every(isVerifiedUnsafeActionEvidence),
                wrongType:isVerifiedUnsafeActionEvidence({...ghost[0],form:'メガグソクムシャ'}),
                wrongGhostMove:isVerifiedUnsafeActionEvidence({...ghost[0],action:'じしん'}),
                wrongGhostDate:isVerifiedUnsafeActionEvidence({...ghost[0],sourceUpdated:'不明'}),
                wrongBounceAbility:isVerifiedUnsafeActionEvidence({...bounce[0],ability:'かげふみ'}),
                wrongBounceMove:isVerifiedUnsafeActionEvidence({...bounce[0],action:'じしん'}),
                wrongBounceForm:isVerifiedUnsafeActionEvidence({...bounce[0],form:'メガアブソルZ'}),
                wrongBounceSource:isVerifiedUnsafeActionEvidence({...bounce[0],mechanicSource:''}),
                safeCount:Object.keys(verifiedMatchupEvidence).length
              };
            }""")
            assert extra_negative == {
                'ghostForms':9,'ghostCount':27,'bounceCount':4,'allValid':True,
                'wrongType':False,'wrongGhostMove':False,'wrongGhostDate':False,
                'wrongBounceAbility':False,'wrongBounceMove':False,
                'wrongBounceForm':False,'wrongBounceSource':False,'safeCount':0
            }, extra_negative
            # Use six distinct slots with no other Ghost type to isolate warnings.
            for i,name in enumerate(['メガヤミラミ','アシレーヌ','ドドゲザン',
                                     'ニンフィア','カバルドン','ペリッパー']):
                page.locator(f'#foe{i}').fill(name)
            for opponent,expected,needle in [
                ('メガヤミラミ',5,'ステルスロック反射（条件付き）'),
                ('メガジュペッタ',3,'しんそく無効（条件付き）'),
                ('メガユキメノコ',3,'しんくうは無効（条件付き）'),
                ('イダイトウ(オス)',3,'インファイト無効（条件付き）'),
                ('イダイトウ(メス)',3,'しんそく無効（条件付き）'),
                ('ミカルゲ',3,'しんそく無効（条件付き）'),
                ('メガアブソル',2,'あくび反射（条件付き）'),
                ('メガアブソルZ',3,'しんそく無効（条件付き）')
            ]:
                page.locator('#foe0').fill(opponent)
                page.locator('#analyze').click()
                warning=page.locator('#result .verified-unsafe-action')
                assert warning.locator('.line').count()==expected, (opponent,warning.inner_text())
                assert needle in warning.inner_text(), (opponent,needle)
                if opponent=='メガヤミラミ':
                    assert 'ステルスロック反射' in page.locator('#result .risk-matrix').inner_text()
                    assert 'ステルスロック反射' in page.locator('#result .trio-inspector-details').inner_text()
                    assert 'ステルスロック：反射' in page.locator('#result .lead-inspector').inner_text()
                assert page.locator('#result .hero').count()==0
                assert '検証済み対面 0/6匹' in page.locator('#result .evidence-summary').inner_text()
                assert page.evaluate('() => document.documentElement.scrollWidth <= innerWidth + 2')
            # Exact Mega Absol Z must NOT inherit Mega Absol's Magic Bounce.
            page.locator('#foe0').fill('メガアブソルZ')
            page.locator('#analyze').click()
            assert '反射（条件付き）' not in page.locator('#result .verified-unsafe-action').inner_text()
            # The base species must conservatively show BOTH possible Megas.
            page.locator('#foe0').fill('アブソル')
            page.locator('#analyze').click()
            assert 'あくび反射（条件付き）' in page.locator('#result .verified-unsafe-action').inner_text()
            assert 'しんそく無効（条件付き）' in page.locator('#result .verified-unsafe-action').inner_text()
            assert page.locator('#result .hero').count()==0

            # Four historical M-B Mega examples: never promote to current
            # M-C reviewed matchups. X/Y must stay distinct.
            extra=page.evaluate("""() => reviewedOpponentProfiles.slice(10).map(p=>({
              form:p.form,regulation:p.regulation,source:p.source,
              updated:p.updated,item:p.item,ability:p.ability,
              speed:[p.speedMin,p.speedMax],boost:boostedSpeedRange(p),
              valid:isReviewedOpponentProfile(p)
            }))""")
            assert [p['form'] for p in extra]==[
                'メガメタグロス','メガリザードンX',
                'メガライチュウX','メガライチュウY'],extra
            assert [p['speed'] for p in extra]==[
                [117,178],[108,167],[117,178],[135,200]],extra
            assert [p['boost'] for p in extra]==[
                None,[162,250],None,None],extra
            assert all(p['valid'] and 'M-B' in p['regulation'] and
                p['source'].startswith('https://gamewith.jp/pokemon-champions/')
                for p in extra)
            assert extra[2]['ability']=='エレキメイカー'
            assert extra[3]['ability']=='ノーガード'
            speed_gate=page.evaluate("""() => ({
              megaX:reviewedSpeedReferencesFor('メガカイリュー',['メガライチュウX']).map(p=>p.form),
              megaY:reviewedSpeedReferencesFor('メガカイリュー',['メガライチュウY']).map(p=>p.form),
              both:reviewedSpeedReferencesFor('カバルドン',requiredMatchupForms('ライチュウ')).map(p=>p.form),
              unknown:reviewedSpeedReferencesFor('カバルドン',['未確認']).length,
              missingOwn:reviewedSpeedReferencesFor('未登録',requiredMatchupForms('ライチュウ')).length,
              safe:Object.keys(verifiedMatchupEvidence).length
            })""")
            assert speed_gate=={
                'megaX':['メガライチュウX'],
                'megaY':['メガライチュウY'],
                'both':['メガライチュウX','メガライチュウY'],
                'unknown':0,'missingOwn':0,'safe':0},speed_gate
            for i,name in enumerate(['ライチュウ','リザードン','メタグロス',
                                     'アシレーヌ','ガブリアス','ペリッパー']):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#analyze').click()
            assert page.locator('#result .hero').count()==0
            assert '検証済み対面 0/6匹' in page.locator('#result .evidence-summary').inner_text()
            assert page.locator('#result .reviewed-opponent-profile').count()==6
            page.locator('#result .reviewed-opponent-profiles summary').click()
            assert 'M-B（過去の参考型）' in page.locator('#result .reviewed-opponent-profiles').inner_text()
            page.locator('#result .risk-matrix summary').click()
            matrix=page.locator('#result .risk-matrix')
            assert matrix.locator('.matrix-cell').count()==36
            assert matrix.locator('.speed-reference').count()>=18
            matrix_text=matrix.inner_text()
            assert 'メガライチュウX' in matrix_text
            assert 'メガライチュウY' in matrix_text
            assert 'メガリザードンX：ニトロチャージ成功後の素早さ162〜250' in matrix_text
            assert '先制技・持ち物・メガ前の素早さ・実際の型は未確認' in matrix_text
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2')
            # Interactive lead inspector: six opponents, every exact Mega/form
            # branch, source-dated negative actions, no positive safety claim.
            inspection_names=['ゲンガー','リザードン','グソクムシャ',
                              'イエッサン(メス)','メガガブリアスZ','サーフゴー']
            for i,name in enumerate(inspection_names):
                page.locator(f'#foe{i}').fill(name)
            page.locator('#analyze').click()
            inspector=page.locator('#result .lead-inspector')
            assert inspector.count()==1
            assert inspector.locator('.lead-inspector-foe').count()==6
            assert page.locator('#result .hero').count()==0
            audit=page.evaluate("""() => {
              const names=['ゲンガー','リザードン','グソクムシャ',
                           'イエッサン(メス)','メガガブリアスZ','サーフゴー'];
              const rows=leadRiskRows(names,'カバルドン');
              return {
                rows:rows.length,
                gengar:rows[0].branches.map(b=>b.form),
                trap:rows[0].branches.find(b=>b.form==='メガゲンガー').unsafe
                  .some(e=>e.action==='manual-switch' && e.outcome==='blocked'),
                charizard:rows[1].branches.map(b=>b.form),
                quake:rows[1].branches.find(b=>b.form==='メガリザードンY').unsafe
                  .some(e=>e.action==='じしん' && e.outcome==='immune'),
                indeedee:rows[3].branches.map(b=>b.form),
                noSafe:Object.keys(verifiedMatchupEvidence).length===0
              };
            }""")
            assert audit=={
                'rows':6,'gengar':['ゲンガー','メガゲンガー'],
                'trap':True,'charizard':['リザードン','メガリザードンX','メガリザードンY'],
                'quake':True,'indeedee':['イエッサン(メス)'],'noSafe':True
            },audit
            inspector.locator('#lead-inspector-select').select_option('メガカイリュー')
            assert inspector.locator('.lead-inspector-foe').count()==6
            assert inspector.locator('.lead-inspector-veto').count()>=1
            assert inspector.locator('.lead-inspector-conditional').count()>=1
            assert 'しんそく' in inspector.inner_text()
            assert 'この分岐の勝敗・交代先・選出の安全性は未検証' in inspector.inner_text()
            assert page.evaluate("sessionStorage.getItem(LEAD_INSPECTOR_KEY)")=='メガカイリュー'
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2')
            page.reload(wait_until='domcontentloaded')
            assert [page.locator(f'#foe{i}').input_value() for i in range(6)]==inspection_names
            page.locator('#analyze').click()
            assert page.locator('#lead-inspector-select').input_value()=='メガカイリュー'
            assert page.locator('#result .hero').count()==0
            # Manual trio inspection: 3 distinct chosen members x all 6 foes,
            # with every Mega/sex branch, no implicit safe or winning outcome.
            trio=page.locator('#result .trio-inspector-details')
            assert trio.count()==1
            assert trio.locator('.trio-inspector-foe').count()==6
            assert trio.locator('.trio-inspector-cell').count()==18
            assert 'メガゲンガー：通常交代不可' in trio.inner_text()
            assert page.locator('#result .hero').count()==0
            assert [page.locator(f'#trio-inspector-{i}').input_value()
                    for i in range(3)]==[
                        'カバルドン','メガルカリオZ','メガカイリュー']
            page.locator('#trio-inspector-1').select_option('ギルガルド')
            assert trio.locator('.trio-inspector-cell').count()==18
            assert page.locator('#trio-inspector-1').input_value()=='ギルガルド'
            # Duplicate attempt is rejected without losing a previous choice.
            page.locator('#trio-inspector-2').select_option('ギルガルド')
            assert page.locator('#trio-inspector-2').input_value()=='メガカイリュー'
            assert '同じポケモンを2匹選択できません' in page.locator(
                '#trio-inspector-status').inner_text()
            page.locator('#lead-inspector-select').select_option('ギルガルド')
            page.locator('#trio-inspector-1').select_option('ミミッキュ')
            assert page.locator('#lead-inspector-select').input_value()=='カバルドン'
            # Choosing a lead outside the trio replaces slot 3, not a fourth member.
            page.locator('#lead-inspector-select').select_option('ギルガルド')
            assert [page.locator(f'#trio-inspector-{i}').input_value()
                    for i in range(3)]==[
                        'カバルドン','ミミッキュ','ギルガルド']
            assert trio.locator('.trio-inspector-cell').count()==18
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2')
            page.reload(wait_until='domcontentloaded')
            page.locator('#analyze').click()
            assert [page.locator(f'#trio-inspector-{i}').input_value()
                    for i in range(3)]==[
                        'カバルドン','ミミッキュ','ギルガルド']
            assert page.locator('#lead-inspector-select').input_value()=='ギルガルド'
            assert page.locator('#result .trio-inspector-cell').count()==18
            assert page.locator('#result .hero').count()==0
            page.locator('#clear').click()
            assert page.evaluate("sessionStorage.getItem(LEAD_INSPECTOR_KEY)") is None
            assert page.evaluate("sessionStorage.getItem(TRIO_INSPECTOR_KEY)") is None
            assert all(page.locator(f'#foe{i}').input_value()=='' for i in range(6))
            assert not errors, errors
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
