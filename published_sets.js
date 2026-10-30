// Issue #11: exact four-move examples copied as structured FACTS, not as
// opponent move probabilities, universal sets, safe leads, or matchup wins.
// M-A/B examples are historical even when their species is M-C eligible.
const publishedOpponentSetSpecs=Object.freeze([
 {id:'golisopod-mc-bulk',form:'メガグソクムシャ',title:'ビルドきゅうけつ型',
  regulation:'M-C・シングル',item:'グソクムシャナイト',ability:'かたいツメ',speed:60,
  moves:['きゅうけつ','アイアンヘッド','ふいうち','ビルドアップ'],
  priority:[{move:'ふいうち',value:1,condition:'こちらが攻撃技を選び、相手がまだ行動していないときのみ成功'}],
  source:'https://gamewith.jp/pokemon-champions/575652',updated:'2026-10-28'},
 {id:'charizard-y-ma-b-roost',form:'メガリザードンY',title:'はねやすめ搭載特殊アタッカー型',
  regulation:'M-A/M-B・シングル（過去型）',item:'リザードナイトY',ability:'ひでり',speed:120,
  moves:['オーバーヒート','かえんほうしゃ','ソーラービーム','はねやすめ'],priority:[],
  source:'https://gamewith.jp/pokemon-champions/554808',updated:'2026-10-29'},
 {id:'gengar-ma-b-attacker',form:'メガゲンガー',title:'特殊アタッカー型',
  regulation:'M-A/M-B・シングル（過去型）',item:'ゲンガナイト',ability:'かげふみ',speed:200,
  moves:['シャドーボール','ヘドロウェーブ','きあいだま','まもる'],
  priority:[{move:'まもる',value:4,condition:'自身を守る変化技。連続使用は成功率が下がる'}],
  source:'https://gamewith.jp/pokemon-champions/554816',updated:'2026-10-29'},
 {id:'gengar-ma-b-perish',form:'メガゲンガー',title:'ほろびのうた型',
  regulation:'M-A/M-B・シングル（過去型）',item:'ゲンガナイト',ability:'かげふみ',speed:200,
  moves:['シャドーボール','まもる','ほろびのうた','みちづれ'],
  priority:[{move:'まもる',value:4,condition:'自身を守る変化技。連続使用は成功率が下がる'}],
  source:'https://gamewith.jp/pokemon-champions/554816',updated:'2026-10-29'}
]);
const publishedOpponentSets=Object.freeze(publishedOpponentSetSpecs.map(s=>Object.freeze({
 ...s,moves:Object.freeze([...s.moves]),priority:Object.freeze(s.priority.map(p=>Object.freeze({...p})))
})));
const ownPriorityMoves=Object.freeze({'しんくうは':1,'しんそく':2,'かげうち':1,'アクアジェット':1});
const ownStatusMoves=new Set(['あくび','ステルスロック','なまける','わるだくみ','つるぎのまい']);
function isReviewedPublishedSet(s){
 const spec=publishedOpponentSetSpecs.find(x=>x.id===s?.id);
 return !!(spec && s.form===spec.form && supportedNames.has(s.form) &&
  s.title===spec.title && s.regulation===spec.regulation &&
  s.item===spec.item && s.ability===spec.ability && s.speed===spec.speed &&
  s.source===spec.source && s.updated===spec.updated &&
  /^2026-10-\d{2}$/.test(s.updated) &&
  Array.isArray(s.moves) && s.moves.length===4 &&
  s.moves.every((m,i)=>m===spec.moves[i]) &&
  Array.isArray(s.priority) && s.priority.length===spec.priority.length &&
  s.priority.every((p,i)=>p.move===spec.priority[i].move &&
   p.value===spec.priority[i].value && p.condition===spec.priority[i].condition &&
   s.moves.includes(p.move)));
}
function publishedSetsFor(opponents){
 const forms=new Set(opponents.flatMap(requiredMatchupForms));
 return publishedOpponentSets.filter(s=>isReviewedPublishedSet(s) && forms.has(s.form));
}
function publishedSetSpeedOrder(own,s){
 if(!isReviewedPublishedSet(s))return 'unknown';
 const speed=ownLv50Speed[own];
 return !Number.isInteger(speed)?'unknown':speed>s.speed?'before':speed<s.speed?'after':'tie';
}
function publishedSetActionRisk(own,move,s){
 if(!isReviewedPublishedSet(s) || !roster.some(p=>p[0]===own && p[2].split('／').includes(move)))
  return [];
 const ownPriority=ownPriorityMoves[move]||0;
 const ownAttacks=!ownStatusMoves.has(move);
 return s.priority.filter(p=>p.value>0 && (
   (p.move==='ふいうち' && ownAttacks && p.value>=ownPriority) ||
   (p.move==='まもる' && ownAttacks)
 )).map(p=>({
   move:p.move,priority:p.value,
   status:p.move==='ふいうち'?(p.value===ownPriority?'同優先度・素早さ条件':'条件付き先制リスク'):'条件付き防御リスク',
   condition:p.condition
 }));
}
function renderPublishedSetAudit(opponents,trio){
 if(!validInspectedTrio(trio))return '';
 const sets=publishedSetsFor(opponents);
 const rows=sets.map(s=>{
  const speedRows=trio.map(own=>{
   const order=publishedSetSpeedOrder(own,s);
   const speedLabel=order==='before'?'掲載型より先に行動する参考値':
    order==='after'?'掲載型が先に行動する参考値':
    order==='tie'?'掲載型と同速・行動順不定':'実数値未登録';
   const risks=roster.find(p=>p[0]===own)[2].split('／').flatMap(move=>
    publishedSetActionRisk(own,move,s).map(r=>move+' 対 '+r.move+'：'+r.status));
   return '<div class="line published-set-own"><b>'+esc(own)+' '+esc(ownLv50Speed[own])+
    '：'+esc(speedLabel)+'</b>'+
    (risks.length?'<div class="warn">⚠️ '+risks.map(esc).join('／')+'</div>':'')+
    '<div class="muted">素早さは同優先度・無補正の掲載例のみ。技・フィールド・持ち物・相手の別型で変動します。</div></div>';
  }).join('');
  return '<details class="published-set-row"><summary>'+esc(s.form)+'｜'+esc(s.title)+
   '（Lv50 S'+s.speed+'）</summary><div class="tag">'+esc(s.regulation)+
   '／'+esc(s.item)+'／'+esc(s.ability)+'</div>'+
   '<div>出典に掲載された4技：'+s.moves.map(esc).join('／')+'</div>'+
   (s.priority.length?'<div class="warn">優先度・条件：'+s.priority.map(p=>
     esc(p.move)+' +'+p.value+'（'+esc(p.condition)+'）').join('／')+'</div>':'')+
   speedRows+'<div class="muted">出典更新 '+esc(s.updated)+
   ' ／ <a href="'+esc(s.source)+'" target="_blank" rel="noopener noreferrer">掲載育成論</a>'+
   '。掲載型が存在することと、実際の相手の型・選出・安全な先発が確認されたことは別です。</div></details>';
 }).join('');
 return '<section class="line published-set-audit"><details><summary>出典で4技・持ち物・特性・Lv50実数値を確認した掲載型 '+
  sets.length+'件（選択3匹と比較／推奨なし）</summary>'+
  '<p class="muted">現行M-Cの掲載型と過去M-A/Bの参考型を区別。相手がこの型を採用した確率は不明です。'+
  '素早さ・優先度だけではダメージ、行動可否、交代安全、勝敗は証明できません。別の型・メガ前の分岐は未検証です。</p>'+
  (rows||'<p class="muted">相手6匹に一致する掲載型なし。安全を意味しません。</p>')+
  '</details></section>';
}
