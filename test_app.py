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
            # Unknown Pokémon must not crash the app or inject markup.
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
    print('PASS: 3 cases x 2 viewport sizes; selection, lead, clear, overflow, runtime errors')

if __name__=='__main__': main()
