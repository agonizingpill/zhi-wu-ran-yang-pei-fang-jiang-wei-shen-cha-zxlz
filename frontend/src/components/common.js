import {escape,decimal} from '../utils.js';
import {TRIAL_STATES} from '../constants.js';
export const status=(value)=>`<span class="status ${escape(value)}">${escape(TRIAL_STATES[value]||value)}</span>`;
export const heading=(n,title,text)=>`<section class="title"><div><div class="eyebrow">QISE LAB / ${n}</div><h1>${title}</h1><p>${text}</p></div></section>`;
export const recipeOptions=(rows)=>rows.map(r=>`<option value="${r.id}">${escape(r.code)} · ${escape(r.name)}${r.locked?' / 冻结':''}</option>`).join('');
export function spectrum(sample){const pts=sample.spectrum.map((v,i)=>`${i*14},${120-v*110}`).join(' ');return `<svg viewBox="0 0 490 140" aria-label="${escape(sample.lot)} 光谱"><path d="M0 120H490" stroke="currentColor" opacity=".2"/><polyline points="${pts}" fill="none" stroke="currentColor" stroke-width="2"/><text x="0" y="139" font-size="10">380nm</text><text x="450" y="139" font-size="10">730nm</text></svg>`;}
export function swatchTable(rows){return `<table><thead><tr><th>批号</th><th>配方</th><th>L*</th><th>a*</th><th>b*</th></tr></thead><tbody>${rows.map(s=>`<tr><td>${escape(s.lot)}</td><td>${s.recipe_id}</td><td>${decimal(s.l)}</td><td>${decimal(s.a)}</td><td>${decimal(s.b)}</td></tr>`).join('')}</tbody></table>`;}
