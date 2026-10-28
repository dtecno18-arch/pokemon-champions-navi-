import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

// Exact labels from the official M-C eligible list (2026-09-09).
// Do not merge distinct forms: Tauros breeds, Rotom appliances, size/sex.
const cases = [
  ['ケンタロス (パルデアのすがた・コンバットしゅ)', 'パルデアケンタロス(かくとう)'],
  ['ケンタロス (パルデアのすがた・ブレイズしゅ)', 'パルデアケンタロス(ほのお)'],
  ['ケンタロス (パルデアのすがた・ウォーターしゅ)', 'パルデアケンタロス(みず)'],
  ['ロトム (ロトムのすがた)', 'ロトム'],
  ['ロトム (ヒートロトム)', 'ヒートロトム'],
  ['ロトム (ウォッシュロトム)', 'ウォッシュロトム'],
  ['ロトム (フロストロトム)', 'フロストロトム'],
  ['ロトム (スピンロトム)', 'スピンロトム'],
  ['ロトム (カットロトム)', 'カットロトム'],
  ['パンプジン (ちゅうだましゅ)', 'パンプジン(ちゅうだま)'],
  ['パンプジン (こだましゅ)', 'パンプジン(こだま)'],
  ['パンプジン (おおだましゅ)', 'パンプジン(おおだま)'],
  ['パンプジン (ギガだましゅ)', 'パンプジン(ギガだま)'],
  ['ルガルガン (まひるのすがた)', 'ルガルガン(まひる)'],
  ['ルガルガン (まよなかのすがた)', 'ルガルガン(まよなか)'],
  ['ルガルガン (たそがれのすがた)', 'ルガルガン(たそがれ)'],
  ['ニャオニクス (オスのすがた)', 'ニャオニクス(オス)'],
  ['ニャオニクス (メスのすがた)', 'ニャオニクス(メス)'],
  ['イダイトウ (オスのすがた)', 'イダイトウ(オス)'],
  ['イダイトウ (メスのすがた)', 'イダイトウ(メス)'],
];
const html = fs.readFileSync('index.html', 'utf8');
const match = html.match(/const formAliases=Object\.freeze\((\{[\s\S]*?\})\);/);
assert.ok(match, 'formAliases must be available');
const aliases = vm.runInNewContext('(' + match[1] + ')');
const key = name => {
  const normalized = name.normalize('NFKC').replace(/[\s　・･]/g, '');
  return aliases[normalized] || normalized;
};
for (const [official, expected] of cases) {
  assert.equal(key(official), expected, official);
}
assert.equal(new Set(cases.map(x => key(x[0]))).size, cases.length,
  'distinct official forms must not collapse to one matchup form');
const rotomList = html.match(/const officialMcRosterKnownForms=(\[[^;]+\]);/);
assert.ok(rotomList, 'official M-C Rotom forms must be explicit input candidates');
const rotom = vm.runInNewContext(rotomList[1]);
assert.deepEqual(Array.from(rotom), [
  'ロトム','ヒートロトム','ウォッシュロトム',
  'フロストロトム','スピンロトム','カットロトム'
]);
assert.equal(new Set(rotom).size, 6, 'Rotom forms must remain distinct');
console.log('PASS: 20 official M-C aliases + 6 Rotom forms + distinct form identity');
