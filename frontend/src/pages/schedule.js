import {store,refresh} from '../store.js';import {api,session} from '../api.js';import {heading} from '../components/common.js';import {escape,decimal,formData,notify,localTime} from '../utils.js';
const stateLabels={planned:'待排',started:'在染',completed:'已完工'};
const outcomeLabels={no_transition:'首缸免判定',no_wash_ok:'免洗可行 · 留出检验',wash_required:'要求清洗'};
const kindLabels={plan:'排产登记',judge:'换色判定',reschedule:'改排',wash:'确认清洗',void:'凭据失效',start:'开染',block:'开染拦截',complete:'完工登记',history:'历史换色'};
const startKeys={};
const machine=id=>store.machines.find(m=>m.id===id);
const voucherOf=s=>store.vouchers.find(v=>v.next_slot_id===s.id);
const slotEvents=s=>store.scheduleEvents.filter(e=>e.slot_id===s.id);
const anchorOptions=(mid,exclude)=>`<option value="">队尾（追加）</option>`+store.slots.filter(s=>s.machine_id===mid&&s.state==='planned'&&s.id!==exclude).map(s=>`<option value="${s.id}">插到 ${escape(s.code)}（顺位${s.seq}）之前</option>`).join('');
function judgmentBadge(s){
 if(s.stale)return `<span class="status rejected">判定失效待重算</span>`;
 const o=s.judgment?.outcome;
 if(!o)return '';
 if(o==='no_wash_ok')return `<span class="status approved">${outcomeLabels[o]}</span>`;
 if(o==='wash_required')return `<span class="status rejected">${outcomeLabels[o]}</span>`;
 return `<span class="status">${outcomeLabels[o]}</span>`;
}
function voucherBadge(s){
 const v=voucherOf(s);
 if(!v)return s.judgment?.outcome==='wash_required'?`<span class="status rejected">缺清洗凭据</span>`:'';
 return `<span class="status ${v.state==='active'?'approved':v.state==='void'?'rejected':''}">凭据#${v.id} ${{active:'有效',used:'已核销',void:'已失效'}[v.state]}</span>`;
}
function detailText(e){
 const d=e.detail||{};
 if(e.kind==='plan')return `上机 ${escape(d.machine)} 顺位${d.seq}${d.inserted?'（插单）':''} → ${outcomeLabels[d.outcome]||escape(d.outcome)}`;
 if(e.kind==='judge')return `${outcomeLabels[d.outcome]||escape(d.outcome)}：${escape(d.reason)}`;
 if(e.kind==='reschedule')return `${escape(d.from?.machine)} 顺位${d.from?.seq} → ${escape(d.to?.machine)} 顺位${d.to?.seq}`;
 if(e.kind==='wash')return `凭据#${d.voucher_id} ${escape((d.pair||[]).join('→'))} 确认人 ${escape(d.confirmed_by)}`;
 if(e.kind==='void')return `凭据#${d.voucher_id} ${escape((d.pair||[]).join('→'))}：${escape(d.reason)}`;
 if(e.kind==='start')return `判定${outcomeLabels[d.outcome]||escape(d.outcome)}${d.voucher_id?` 核销凭据#${d.voucher_id}`:''} · key=${escape(d.request_key)}`;
 if(e.kind==='block')return escape(d.reason);
 if(e.kind==='complete')return `首测ΔE=${d.first_delta_e}（${d.washed?'已清洗':'免洗'}）${d.record_id?`生成换色记录#${d.record_id}`:''}`;
 if(e.kind==='history')return `${escape(d.machine)} ${escape((d.pair||[]).join('→'))} ΔE=${d.first_delta_e} ${d.washed?'已清洗':'免洗'}`;
 return escape(JSON.stringify(d));
}
function judgmentDetail(s){
 const j=s.judgment;
 if(!j)return '<p class="hint">尚无判定记录。</p>';
 const ev=(j.evidence||[]).map(e=>`<div class="evt">记录#${e.record_id} ${escape(e.prev_code)}→${escape(e.next_code)} 首测ΔE=${e.first_delta_e} · 配方距离 ${e.prev_distance}/${e.next_distance}</div>`).join('')||'<div class="evt">无匹配免洗记录</div>';
 return `<div class="rule">判定：${outcomeLabels[j.outcome]||escape(j.outcome)}<br>依据：${escape(j.reason)}<br>前后缸：${escape(j.prev_code||'—')} → ${escape(s.code)}${j.depth_before!==undefined?` · 浓度合计 ${j.depth_before}→${j.depth_after}`:''}<br>同机免洗证据 ${j.evidence_count}/${j.evidence_min} 条（配方距离容差 ${j.tolerance}，ΔE 门限 ${j.delta_e_limit}） · 判定于 ${escape(j.decided_at)}</div>${ev}`;
}
function eventList(s){
 const evts=slotEvents(s);
 if(!evts.length)return '<p class="hint">暂无事件。</p>';
 return evts.map(e=>`<div class="evt ${e.kind==='block'?'blocked':''}"><strong>${kindLabels[e.kind]||escape(e.kind)}</strong> · ${localTime(e.at)} · ${escape(e.actor)}<br>${detailText(e)}</div>`).join('');
}
function slotCard(s){
 const m=machine(s.machine_id),snap=s.recipe_snapshot,v=voucherOf(s),canEdit=session().role!=='viewer';
 const actions=[];
 if(s.state==='planned'){
  actions.push(`<button type="button" data-start="${s.id}" ${!canEdit?'disabled':''}>开染</button>`);
  if(s.stale)actions.push(`<button type="button" data-rejudge="${s.id}" ${!canEdit?'disabled':''}>重算判定</button>`);
  if(!s.stale&&s.judgment?.outcome==='wash_required'&&(!v||v.state!=='active'))actions.push(`<button type="button" data-wash="${s.id}" ${session().role!=='admin'?'disabled':''}>主管确认清洗</button>`);
 }
 if(s.state==='started')actions.push(`<form class="complete-form" data-key="${s.id}"><label>首测色差 ΔE<input name="first_delta_e" type="number" step=".01" min="0" max="100" value="1.0" required></label><button ${!canEdit?'disabled':''}>完工登记</button></form>`);
 return `<article class="trial slot" data-id="${s.id}"><div class="code">${escape(m?.code)} ${escape(m?.name)} · 顺位 ${s.seq} · 登记 ${escape(s.created_by)}</div><h3>${escape(s.code)} <span class="status">${stateLabels[s.state]}</span>${judgmentBadge(s)}${voucherBadge(s)}</h3><div class="metricline"><div>配方<strong>${escape(snap.code)}</strong></div><div>浓度 A/B/C<strong>${snap.dye_a} / ${snap.dye_b} / ${snap.dye_c}</strong></div><div>重量<strong>${decimal(s.kg,0)} kg</strong></div></div><p class="hint">前缸：${s.current_prev_code?escape(s.current_prev_code):'—（本机首缸）'}${s.inspection_reserved&&s.state!=='completed'?' · 已留出首测检验':''}${s.started_at?` · 开染 ${localTime(s.started_at)}`:''}${s.completed_at?` · 完工 ${localTime(s.completed_at)}`:''}</p>${s.state==='planned'?`<form class="rs-form" data-key="${s.id}"><div class="grid2"><label>改排染机<select name="machine_id" class="rs-machine" data-exclude="${s.id}">${store.machines.map(mm=>`<option value="${mm.id}" ${mm.id===s.machine_id?'selected':''}>${escape(mm.code)} ${escape(mm.name)}</option>`).join('')}</select></label><label>插位<select name="before_slot_id" class="rs-anchor">${anchorOptions(s.machine_id,s.id)}</select></label></div><div class="actions">${actions.join('')}<button ${!canEdit?'disabled':''}>提交改排</button></div></form>`:`<div class="actions">${actions.join('')}</div>`}<details class="evidence"><summary>判定依据与拦截原因（${slotEvents(s).length} 条事件）</summary>${judgmentDetail(s)}${eventList(s)}</details></article>`;
}
export function render(){
 const canEdit=session().role!=='viewer';
 return heading('10','深色接浅色先算证据，再决定洗不洗','同机历次免洗换色的前后配方与首测色差预测免洗超差风险；证据不足要求清洗。开染以同机实际完工上一缸为准，插单改排后凭据失效、重算前拦截。')
 +`<div class="machine-grid">${store.machines.map(m=>`<section class="panel machine"><h2>${escape(m.code)} · ${escape(m.name)}</h2><p class="hint">待排 ${m.queued} · 在染 ${m.running} · 留出首测检验 ${m.inspection_reserved}</p>${store.slots.filter(s=>s.machine_id===m.id).map(slotCard).join('')||'<div class="empty">本机暂无排产</div>'}</section>`).join('')}</div>`
 +`<div class="split subhead"><section class="panel"><h2>排产 / 插单</h2><form id="plan-form"><label>染机<select name="machine_id" id="plan-machine">${store.machines.map(m=>`<option value="${m.id}">${escape(m.code)} ${escape(m.name)}</option>`).join('')}</select></label><label>缸号<input name="code" placeholder="Q-1104" required></label><label>配方<select name="recipe_id">${store.recipes.map(r=>`<option value="${r.id}">${escape(r.code)} · ${escape(r.name)}（A${r.dye_a}/B${r.dye_b}/C${r.dye_c}）</option>`).join('')}</select></label><label>重量 / kg<input name="kg" type="number" min="1" max="10000" value="300"></label><label>插位<select name="before_slot_id" id="plan-anchor">${anchorOptions(store.machines[0]?.id,0)}</select></label><button class="primary" ${!canEdit?'disabled':''}>登记排产</button></form><div class="rule">登记即按当前前缸自动判定：同机免洗证据 ≥2 条且首测 ΔE≤3 才允许免洗并留出检验；否则要求清洗。插单会使受影响清洗凭据立即失效。</div></section>`
 +`<section class="panel"><h2>登记历史换色</h2><form id="history-form"><div class="grid3"><label>染机<select name="machine_id">${store.machines.map(m=>`<option value="${m.id}">${escape(m.code)}</option>`).join('')}</select></label><label>前缸配方<select name="prev_recipe_id">${store.recipes.map(r=>`<option value="${r.id}">${escape(r.code)}</option>`).join('')}</select></label><label>后缸配方<select name="next_recipe_id">${store.recipes.map(r=>`<option value="${r.id}" ${r===store.recipes[1]?'selected':''}>${escape(r.code)}</option>`).join('')}</select></label></div><div class="grid3"><label>首测色差 ΔE<input name="first_delta_e" type="number" step=".01" min="0" max="100" value="1.2" required></label><label>换色方式<select name="washed"><option value="">免洗直换</option><option value="yes">已清洗</option></select></label><label>备注<input name="note" placeholder="班次 / 工艺说明"></label></div><button class="primary" ${!canEdit?'disabled':''}>登记换色记录</button></form><div class="rule">只有“免洗直换”记录进入证据池；完工登记也会自动生成换色记录。清洗记录仅留档，不作免洗判定依据。</div></section></div>`
 +`<div class="split subhead"><section class="panel"><h2>清洗凭据</h2><table><thead><tr><th>凭据</th><th>前后两缸</th><th>状态</th><th>确认 / 核销 / 失效</th></tr></thead><tbody>${store.vouchers.map(v=>`<tr><td>#${v.id} · ${escape(machine(v.machine_id)?.code)}</td><td>${escape(v.prev_code)} → ${escape(v.next_code)}</td><td><span class="status ${v.state==='active'?'approved':v.state==='void'?'rejected':''}">${{active:'有效',used:'已核销',void:'已失效'}[v.state]}</span></td><td class="hint">${escape(v.confirmed_by)}${v.used_key?`<br>核销 key ${escape(v.used_key)}`:''}${v.void_reason?`<br>${escape(v.void_reason)}`:''}</td></tr>`).join('')||'<tr><td colspan="4" class="hint">暂无清洗凭据</td></tr>'}</tbody></table><div class="rule">凭据只对登记时的前后两缸有效；插单或改排改变相邻关系即失效，须重算判定后重新确认清洗。</div></section>`
 +`<section class="panel"><h2>判定与拦截回看</h2>${store.scheduleEvents.slice(0,30).map(e=>{const s=store.slots.find(x=>x.id===e.slot_id);return `<div class="evt ${e.kind==='block'?'blocked':''}"><strong>${kindLabels[e.kind]||escape(e.kind)}</strong> · ${localTime(e.at)} · ${escape(e.actor)}${s?` · ${escape(s.code)}`:''}<br>${detailText(e)}</div>`}).join('')||'<p class="hint">暂无事件。</p>'}</section></div>`
 +`<section class="panel subhead"><h2>历史换色证据池</h2><table><thead><tr><th>机台</th><th>前配方 → 后配方</th><th>方式</th><th>首测 ΔE</th><th>来源</th><th>登记</th></tr></thead><tbody>${store.changeRecords.map(r=>`<tr><td>${escape(machine(r.machine_id)?.code)}</td><td>${escape(r.prev_snapshot.code)}（${r.prev_snapshot.dye_a}/${r.prev_snapshot.dye_b}/${r.prev_snapshot.dye_c}）→ ${escape(r.next_snapshot.code)}（${r.next_snapshot.dye_a}/${r.next_snapshot.dye_b}/${r.next_snapshot.dye_c}）</td><td>${r.washed?'已清洗':'<strong>免洗</strong>'}</td><td class="${r.first_delta_e>3?'blocked':''}">${decimal(r.first_delta_e,2)}${r.first_delta_e>3?' 超差':''}</td><td>${r.source==='auto'?'完工自动':'人工登记'}</td><td class="hint">${escape(r.recorded_by)} · ${escape(r.note)}</td></tr>`).join('')||'<tr><td colspan="6" class="hint">暂无换色记录</td></tr>'}</tbody></table></section>`;
}
export function bind(render){
 const canEdit=session().role!=='viewer';
 async function run(fn,msg){try{await fn();await refresh();render();if(msg)notify(msg);}catch(e){notify(e.message);await refresh();render();}}
 const planForm=document.querySelector('#plan-form');
 if(planForm){
  const pm=document.querySelector('#plan-machine'),pa=document.querySelector('#plan-anchor');
  pm.onchange=()=>{pa.innerHTML=anchorOptions(Number(pm.value),0);};
  planForm.onsubmit=e=>{e.preventDefault();let d=formData(e.target);run(()=>api('/schedule/slots','POST',{machine_id:Number(d.machine_id),code:d.code,recipe_id:Number(d.recipe_id),kg:Number(d.kg),before_slot_id:d.before_slot_id?Number(d.before_slot_id):null}),'排产已登记并完成换色判定');};
 }
 const histForm=document.querySelector('#history-form');
 if(histForm)histForm.onsubmit=e=>{e.preventDefault();let d=formData(e.target);run(()=>api('/schedule/history','POST',{machine_id:Number(d.machine_id),prev_recipe_id:Number(d.prev_recipe_id),next_recipe_id:Number(d.next_recipe_id),washed:!!d.washed,first_delta_e:Number(d.first_delta_e),note:d.note||''}),'历史换色已登记，证据池已更新');};
 document.querySelectorAll('.rs-machine').forEach(sel=>sel.onchange=()=>{sel.closest('.rs-form').querySelector('.rs-anchor').innerHTML=anchorOptions(Number(sel.value),Number(sel.dataset.exclude));});
 document.querySelectorAll('.rs-form').forEach(f=>f.onsubmit=e=>{e.preventDefault();let d=formData(f);run(()=>api('/schedule/slots/'+f.dataset.key+'/reschedule','POST',{machine_id:Number(d.machine_id),before_slot_id:d.before_slot_id?Number(d.before_slot_id):null}),'改排完成，受影响凭据已失效，相关缸次需重算判定');});
 document.querySelectorAll('[data-rejudge]').forEach(b=>b.onclick=()=>run(()=>api('/schedule/slots/'+b.dataset.rejudge+'/rejudge','POST',{}),'判定已按当前前后缸重算'));
 document.querySelectorAll('[data-wash]').forEach(b=>b.onclick=()=>run(()=>api('/schedule/vouchers','POST',{slot_id:Number(b.dataset.wash)}),'清洗已确认，凭据生效'));
 document.querySelectorAll('[data-start]').forEach(b=>b.onclick=async()=>{
  const id=Number(b.dataset.start);startKeys[id]=startKeys[id]||`S${id}-${crypto.randomUUID()}`;
  try{const r=await api(`/schedule/slots/${id}/start`,'POST',{request_key:startKeys[id]});delete startKeys[id];await refresh();render();notify(r.result==='replayed'?'开染此前已生效，重试安全返回（凭据未重复核销）':'已开染，判定依据与凭据核销留档');}
  catch(e){notify(`开染被拦截：${e.message}`);await refresh();render();}
 });
 document.querySelectorAll('.complete-form').forEach(f=>f.onsubmit=e=>{e.preventDefault();let d=formData(f);run(()=>api('/schedule/slots/'+f.dataset.key+'/complete','POST',{first_delta_e:Number(d.first_delta_e)}),'完工已登记，换色记录进入证据池');});
}
