// Issue #11: source-reviewed adverse lead/action scenarios, never safe answers.
// Every case is conditional and bound to an exact opposing form and own lead.
// Existing negative action evidence is the mechanical gate for exact vetoes.
// A priority warning is NOT an ineffective move, damage calculation or KO proof.
const adverseLeadScenarios=Object.freeze([
 Object.freeze({
  form:'メガグソクムシャ',ownLead:'カバルドン',ownAction:'ステルスロック',
  opponentMove:'であいがしら',outcome:'priority-risk',
  condition:'相手がメガグソクムシャにメガシンカ済みで、登場後最初の行動に「であいがしら」を選び、技が成功する場合。',
  warning:'であいがしらは優先度+2。ステルスロックを選ぶ前に攻撃され得ます。ダメージ・行動保証は未検証。ふいうちは変化技への回答になりません。',
  exception:'であいがしらを採用していない、登場後最初の行動ではない、先制技を妨げる条件がある場合は別分岐。',
  source:'https://gamewith.jp/pokemon-champions/575652',updated:'2026-10-28',
  reviewed:true,scope:'verified-adverse-lead',confidence:'conditional-risk'
 }),
 Object.freeze({
  form:'メガリザードンY',ownLead:'カバルドン',ownAction:'じしん',
  opponentMove:'ひこうタイプ',outcome:'immune',
  condition:'メガリザードンYのひこうタイプが有効で、通常のタイプ相性が適用される場合。',
  warning:'じしんは無効。通常リザードンとメガYに同じタイプ無効はありますが、メガXには継承しません。',
  exception:'じゅうりょく・はねやすめなど、ひこうタイプの地面無効が失われる場合は再判定。',
  source:'https://gamewith.jp/pokemon-champions/554808',updated:'2026-10-29',
  reviewed:true,scope:'verified-adverse-lead',confidence:'mechanic-veto'
 }),
 Object.freeze({
  form:'メガゲンガー',ownLead:'カバルドン',ownAction:'manual-switch',
  opponentMove:'かげふみ',outcome:'blocked',
  condition:'相手がメガゲンガーにメガシンカ済みで、かげふみが有効な間。',
  warning:'カバルドンは非ゴーストのため通常交代できません。交代を前提に初手を選ばないでください。',
  exception:'メガ前ゲンガー、かげふみ無効、交代技など特殊な例外は別分岐。',
  source:'https://gamewith.jp/pokemon-champions/554816',updated:'2026-10-28',
  reviewed:true,scope:'verified-adverse-lead',confidence:'mechanic-veto'
 }),
 Object.freeze({
  form:'メガゲンガー',ownLead:'メガルカリオZ',ownAction:'しんくうは',
  opponentMove:'ゴーストタイプ',outcome:'immune',
  condition:'相手がメガゲンガー（ゴースト・どく）で通常のタイプ相性が適用される場合。',
  warning:'かくとう技のしんくうはは無効。先制できても攻撃は通りません。',
  exception:'タイプ相性無効を変更する特殊な効果は別分岐。',
  source:'https://gamewith.jp/pokemon-champions/554816',updated:'2026-10-28',
  reviewed:true,scope:'verified-adverse-lead',confidence:'mechanic-veto'
 }),
 Object.freeze({
  form:'メガゲンガー',ownLead:'メガカイリュー',ownAction:'しんそく',
  opponentMove:'ゴーストタイプ',outcome:'immune',
  condition:'相手がメガゲンガー（ゴースト・どく）で通常のタイプ相性が適用される場合。',
  warning:'ノーマル技のしんそくは無効。先制できても攻撃は通りません。',
  exception:'タイプ相性無効を変更する特殊な効果は別分岐。',
  source:'https://gamewith.jp/pokemon-champions/554816',updated:'2026-10-28',
  reviewed:true,scope:'verified-adverse-lead',confidence:'mechanic-veto'
 }),
 Object.freeze({"form":"メガグソクムシャ","ownLead":"カバルドン","ownAction":"じしん","opponentMove":"であいがしら","outcome":"priority-risk","condition":"メガグソクムシャが登場後最初の技として「であいがしら」(+2)を成功させ、こちらが通常優先度の「じしん」を選んだ場合。","warning":"であいがしらはじしんより先に行動します。ダメージ・行動不能・勝敗は未検証。","exception":"であいがしら未採用、初手以外、技が失敗する条件では異なる。","source":"https://gamewith.jp/pokemon-champions/575652","updated":"2026-10-28","reviewed":true,"scope":"verified-adverse-lead","confidence":"conditional-risk"}),
 Object.freeze({"form":"メガグソクムシャ","ownLead":"カバルドン","ownAction":"あくび","opponentMove":"であいがしら","outcome":"priority-risk","condition":"メガグソクムシャが登場後最初の技として「であいがしら」(+2)を成功させ、こちらが通常優先度の「あくび」を選んだ場合。","warning":"あくびより先に攻撃され得ます。あくびの成功や次ターンの生存は未検証。ふいうちは変化技に失敗します。","exception":"であいがしら未採用、初手以外、技が失敗する条件では異なる。","source":"https://gamewith.jp/pokemon-champions/575652","updated":"2026-10-28","reviewed":true,"scope":"verified-adverse-lead","confidence":"conditional-risk"}),
 Object.freeze({"form":"メガグソクムシャ","ownLead":"カバルドン","ownAction":"なまける","opponentMove":"であいがしら","outcome":"priority-risk","condition":"メガグソクムシャが登場後最初の技として「であいがしら」(+2)を成功させ、こちらが通常優先度の「なまける」を選んだ場合。","warning":"回復前に先制攻撃され得ます。回復が間に合うか、被ダメージ・勝敗は未検証。","exception":"であいがしら未採用、初手以外、技が失敗する条件では異なる。","source":"https://gamewith.jp/pokemon-champions/575652","updated":"2026-10-28","reviewed":true,"scope":"verified-adverse-lead","confidence":"conditional-risk"}),
 Object.freeze({"form":"メガグソクムシャ","ownLead":"メガルカリオZ","ownAction":"しんくうは","opponentMove":"であいがしら","outcome":"priority-risk","condition":"メガグソクムシャが登場後最初の技として「であいがしら」(+2)、メガルカリオZが「しんくうは」(+1)を選ぶ場合。","warning":"+2のであいがしらが+1のしんくうはより先。命中・ダメージ・勝敗は未検証。","exception":"であいがしら未採用、初手以外、優先度を変更する特殊条件では異なる。","source":"https://gamewith.jp/pokemon-champions/575652","updated":"2026-10-28","reviewed":true,"scope":"verified-adverse-lead","confidence":"conditional-risk"}),
 Object.freeze({"form":"メガグソクムシャ","ownLead":"ミミッキュ","ownAction":"かげうち","opponentMove":"であいがしら","outcome":"priority-risk","condition":"メガグソクムシャが登場後最初の技として「であいがしら」(+2)、ミミッキュが「かげうち」(+1)を選ぶ場合。","warning":"+2のであいがしらが+1のかげうちより先。ばけのかわ、ダメージ・勝敗は未検証。","exception":"であいがしら未採用、初手以外、優先度を変更する特殊条件では異なる。","source":"https://gamewith.jp/pokemon-champions/575652","updated":"2026-10-28","reviewed":true,"scope":"verified-adverse-lead","confidence":"conditional-risk"}),
 Object.freeze({"form":"メガグソクムシャ","ownLead":"メガカイリュー","ownAction":"しんそく","opponentMove":"であいがしら","outcome":"priority-tie-risk","condition":"メガグソクムシャが登場後最初の技として「であいがしら」(+2)、メガカイリューが「しんそく」(+2)を選ぶ場合。","warning":"双方優先度+2。素早さやその他の行動順条件次第で相手が先に動き得ます。先手保証・勝敗は未検証。","exception":"であいがしら未採用、初手以外、行動順補正や優先度変更がある場合は異なる。","source":"https://gamewith.jp/pokemon-champions/575652","updated":"2026-10-28","reviewed":true,"scope":"verified-adverse-lead","confidence":"conditional-risk"}),
 Object.freeze({"form":"メガゲンガー","ownLead":"メガルカリオZ","ownAction":"manual-switch","opponentMove":"かげふみ","outcome":"blocked","condition":"メガゲンガーがメガシンカ済みで「かげふみ」が有効、非ゴーストのメガルカリオZが場にいる場合。","warning":"メガルカリオZは通常交代できません。味方のゴーストタイプへの交代も通常は不可能です。","exception":"メガ前ゲンガー、かげふみ無効、交代技・特殊な例外は別分岐。","source":"https://gamewith.jp/pokemon-champions/554816","updated":"2026-10-28","reviewed":true,"scope":"verified-adverse-lead","confidence":"mechanic-veto"}),
 Object.freeze({"form":"メガゲンガー","ownLead":"メガカイリュー","ownAction":"manual-switch","opponentMove":"かげふみ","outcome":"blocked","condition":"メガゲンガーがメガシンカ済みで「かげふみ」が有効、非ゴーストのメガカイリューが場にいる場合。","warning":"メガカイリューは通常交代できません。交代先のタイプではなく現在場にいる側のタイプを確認してください。","exception":"メガ前ゲンガー、かげふみ無効、交代技・特殊な例外は別分岐。","source":"https://gamewith.jp/pokemon-champions/554816","updated":"2026-10-28","reviewed":true,"scope":"verified-adverse-lead","confidence":"mechanic-veto"}),
 Object.freeze({"form":"メガゲンガー","ownLead":"ギルガルド","ownAction":"インファイト","opponentMove":"ゴーストタイプ","outcome":"immune","condition":"メガゲンガーがゴースト・どくタイプで通常のタイプ相性が適用される場合。","warning":"ギルガルドのインファイトはメガゲンガーに無効。ギルガルド自身はゴーストのため通常交代制限を受けません。","exception":"みやぶる・きもったま等、タイプ無効を変更する特殊効果は別分岐。","source":"https://gamewith.jp/pokemon-champions/554816","updated":"2026-10-28","reviewed":true,"scope":"verified-adverse-lead","confidence":"mechanic-veto"})
]);
function isReviewedAdverseLeadScenario(s){
 if(!adverseLeadScenarios.includes(s) || s.reviewed!==true ||
    s.scope!=='verified-adverse-lead' ||
    !['mechanic-veto','conditional-risk'].includes(s.confidence) ||
    !supportedNames.has(formKey(s.form)) ||
    !roster.some(p=>p[0]===s.ownLead &&
      (s.ownAction==='manual-switch' || p[2].split('／').includes(s.ownAction))) ||
    !/^https:\/\/gamewith\.jp\/pokemon-champions\/\d+$/.test(s.source) ||
    !/^2026-10-\d{2}$/.test(s.updated) ||
    !s.condition || !s.warning || !s.exception || !s.opponentMove)return false;
 if(s.confidence==='conditional-risk'){
  // A priority warning is source-backed only when the exact own move and
  // opponent move have a reviewed priority relation. Equal priority is NOT
  // a first-move guarantee, and non-damaging actions are still at risk.
  const fromReviewedInteraction=reviewedConditionalLeadInteractions.some(e=>
   isReviewedConditionalLeadInteraction(e) && e.form===s.form &&
   e.own===s.ownLead && e.move===s.ownAction &&
   e.opponentMove===s.opponentMove && e.source===s.source &&
   ((s.outcome==='priority-risk' && e.mechanic==='priority-order') ||
    (s.outcome==='priority-tie-risk' && e.mechanic==='priority-tie')));
  const fromReviewedPair=s.outcome==='priority-risk' &&
   s.ownLead==='カバルドン' &&
   ['じしん','あくび','ステルスロック','なまける'].includes(s.ownAction) &&
   reviewedPairRisks.some(p=>isReviewedPairRisk(p) &&
    p.form===s.form && p.own===s.ownLead && p.source===s.source &&
    p.priorityMoves.some(m=>m.move===s.opponentMove && m.priority===2));
  return fromReviewedInteraction || fromReviewedPair;
 }
 return verifiedUnsafeActionEvidence.some(e=>
   isVerifiedUnsafeActionEvidence(e) && e.form===s.form &&
   e.ownLead===s.ownLead && e.action===s.ownAction &&
   e.outcome===s.outcome);
}
function adverseLeadScenariosFor(opponents,lead){
 const forms=new Set(opponents.flatMap(requiredMatchupForms));
 return adverseLeadScenarios.filter(s=>
  isReviewedAdverseLeadScenario(s) && s.ownLead===lead && forms.has(s.form));
}
function renderAdverseLeadScenarios(opponents,lead){
 const scenarios=adverseLeadScenariosFor(opponents,lead);
 const allBranches=new Set(opponents.flatMap(requiredMatchupForms));
 const documentedBranches=new Set(scenarios.map(s=>s.form));
 return '<section class="line adverse-lead-cases"><h3>出典付き個別対面・初手行動 '+scenarios.length+
  '件（危険条件のみ／安全認定0件）</h3>'+
  '<p class="muted">対象：'+esc(lead)+'。相手の型・技・持ち物は未確定です。'+
  '照合対象 '+allBranches.size+'形態分岐、危険条件が記録された分岐 '+
  documentedBranches.size+'件。記録なしは安全ではなく未検証です。</p>'+
  (scenarios.length?scenarios.map(s=>
   '<div class="warn adverse-lead-case" data-adverse-form="'+esc(s.form)+
   '"><b>⛔ '+esc(s.form)+'｜'+esc(s.ownAction==='manual-switch'?'通常交代':s.ownAction)+
   '：'+esc(s.confidence==='conditional-risk'?'条件付き先制リスク':'条件付き行動不可')+'</b>'+
   '<div>'+esc(s.warning)+'</div><div class="muted">条件：'+esc(s.condition)+
   '</div><div class="muted">例外・未確認：'+esc(s.exception)+'</div>'+
   '<div class="muted">出典更新 '+esc(s.updated)+' ／ <a href="'+esc(s.source)+
   '" target="_blank" rel="noopener noreferrer">GameWith根拠</a></div>'+
   '<div class="muted">この対面の勝敗・安全な交代先・選出3匹は未検証。</div></div>'
  ).join(''):'<div class="muted">この先発と相手6匹に登録された個別危険対面はありません。安全とは判定しません。</div>')+
  '</section>';
}
