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

            # Opponent input survives reload, and explicit clear survives another reload.
            page.reload(wait_until='domcontentloaded')
            assert [page.locator(f'#foe{i}').input_value() for i in range(6)] == unknown_names
            page.locator('#analyze').click()
            assert '0/6匹' in page.locator('#result .risk-banner').inner_text()
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
