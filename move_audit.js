// Issue #11: exact-form negative-evidence audit for manual 3-pokemon selection.
// An absent warning is UNKNOWN, never an effective move, safe lead or win claim.
function auditMoveAgainstOpponent(own,move,opponent){
 const branches=requiredMatchupForms(opponent).map(form=>({
  form,
  vetoes:verifiedUnsafeActionEvidence.filter(e=>
   isVerifiedUnsafeActionEvidence(e) && e.form===form &&
   e.ownLead===own && e.action===move),
  cautions:reviewedConditionalLeadInteractions.filter(e=>
   isReviewedConditionalLeadInteraction(e) && e.forms.includes(form) &&
   e.own===own && e.move===move)
 }));
 const branchCounts={
  danger:branches.filter(b=>b.vetoes.length).length,
  caution:branches.filter(b=>!b.vetoes.length && b.cautions.length).length,
  unknown:branches.filter(b=>!b.vetoes.length && !b.cautions.length).length
 };
 const status=branchCounts.danger?'danger':branchCounts.caution?'caution':'unknown';
 return {own,move,opponent,branches,branchCounts,status};
}
function moveAuditStats(opponents,trio){
 const audits=opponents.flatMap(opponent=>trio.flatMap(own=>{
  const member=roster.find(p=>p[0]===own);
  return member?member[2].split('／').map(move=>
   auditMoveAgainstOpponent(own,move,opponent)):[];
 }));
 return {total:audits.length,danger:audits.filter(a=>a.status==='danger').length,
  caution:audits.filter(a=>a.status==='caution').length,
  unknown:audits.filter(a=>a.status==='unknown').length};
}
function renderMoveAuditRows(opponents,trio,lead){
 if(!validInspectedTrio(trio))return '';
 return opponents.map((opponent,index)=>{
  const cells=trio.flatMap(own=>{
   const member=roster.find(p=>p[0]===own);
   return member[2].split('／').map(move=>{
    const audit=auditMoveAgainstOpponent(own,move,opponent);
    const status=audit.status==='danger'?'⛔ 条件付き無効・反射':
     audit.status==='caution'?'⚠️ 条件付き注意':'未検証（安全とは判定しない）';
    const details=audit.branches.flatMap(b=>[
     ...b.vetoes.map(e=>'<div class="warn move-audit-veto"><b>'+esc(b.form)+
      '：'+esc(e.outcome==='reflected'?'反射':'無効')+'</b><div>'+esc(e.when)+
      '</div><div class="muted">出典確認 '+esc(e.updated)+
      ' ／ <a href="'+esc(e.source)+'" target="_blank" rel="noopener noreferrer">根拠</a></div></div>'),
     ...b.cautions.map(e=>'<div class="warn move-audit-caution"><b>'+esc(b.form)+
      '：'+esc(e.mechanic)+'</b><div>'+esc(e.condition)+
      '</div><div>'+esc(e.effect)+'</div><div class="muted">出典更新 '+
      esc(e.sourceUpdated)+' ／ <a href="'+esc(e.source)+
      '" target="_blank" rel="noopener noreferrer">根拠</a></div></div>'),
     ...(b.vetoes.length||b.cautions.length?[]:[
      '<div class="muted move-audit-unknown-branch">未検証：'+esc(b.form)+
      '（この形態の行動可否・先手・安全性は不明）</div>'])
    ]);
    return '<div class="line move-audit-cell" data-audit-status="'+audit.status+
     '"><b>'+esc(own)+(own===lead?'（先発候補）':'')+'｜'+esc(move)+
     '</b><div>'+esc(status)+'／'+esc('危険 '+audit.branchCounts.danger+
     '・注意 '+audit.branchCounts.caution+'・未検証 '+audit.branchCounts.unknown+
     ' 分岐')+'</div>'+
     (details.length?details.join(''):'<div class="muted">全分岐 '+esc(audit.branches.map(b=>b.form).join('・'))+
      ' に登録済みの個別行動根拠なし。安全・有効・先手・勝敗は不明。</div>')+
     '</div>';
   });
  });
  return '<details class="move-audit-foe"><summary>相手'+(index+1)+' '+esc(opponent)+
   '｜12技の条件付き危険確認（全形態分岐）</summary><p class="muted">分岐：'+
   esc(requiredMatchupForms(opponent).join('・'))+
   '。メガ後の無効・反射を通常形態へ誤適用しません。記載なしは安全を意味しません。</p>'+
   cells.join('')+'</details>';
 }).join('');
}
function buildMoveAudit(opponents,trio,lead){
 const stats=moveAuditStats(opponents,trio);
 return '<details class="line move-audit-details"><summary>選択3匹の4技 × 相手6匹｜'+
  stats.total+'技対面の行動監査（推奨なし）</summary>'+
  '<p class="muted move-audit-summary">⛔既知の条件付き危険 '+stats.danger+
  '／⚠️条件付き注意 '+stats.caution+'／未検証 '+stats.unknown+
  '。安全認定0件。特定分岐の警告を他形態に流用しません。通常交代不可は先発詳細欄で別表示。</p>'+
  '<div id="move-audit-rows"></div></details>';
}

function refreshMoveAudit(opponents,trio,lead){
 const rows=document.querySelector('#move-audit-rows');
 if(!rows)return;
 const stats=moveAuditStats(opponents,trio);
 const summary=document.querySelector('.move-audit-summary');
 if(summary)summary.textContent='⛔既知の条件付き危険 '+stats.danger+
  '／⚠️条件付き注意 '+stats.caution+'／未検証 '+stats.unknown+
  '。安全認定0件。特定分岐の警告を他形態に流用しません。通常交代不可は先発詳細欄で別表示。';
 // Avoid rendering 72 verbose cells on every input or catalog test.
 rows.innerHTML=rows.closest('details')?.open?
  renderMoveAuditRows(opponents,trio,lead):'';
}
document.addEventListener('toggle',event=>{
 if(!event.target.matches?.('.move-audit-details') || !event.target.open)return;
 const opponents=fields.map(f=>f.value.trim());
 if(opponents.length===6 && opponents.every(Boolean))
  refreshMoveAudit(opponents,inspectedTrio,inspectedLead);
},true);
