from datetime import datetime
from sqlalchemy import select,update
from fastapi import HTTPException
from .models import DyeRecipe
from .schedule_models import DyeMachine,ScheduleSlot,ColorChangeRecord,CleaningVoucher,ScheduleEvent
from .recipe_service import log

FORMULA_TOLERANCE=0.8   # 前后配方浓度距离容差（A/B/C 浓度欧氏距离）
EVIDENCE_MIN=2          # 免洗判定所需同机证据最少条数
DELTA_E_LIMIT=3.0       # 首测色差超差门限

def event(db,slot_id,kind,user,detail):
    db.add(ScheduleEvent(slot_id=slot_id,kind=kind,actor=user.email if hasattr(user,'email') else str(user),detail=detail))

def snapshot_of(recipe):
    return {'id':recipe.id,'code':recipe.code,'name':recipe.name,'dye_a':recipe.dye_a,'dye_b':recipe.dye_b,'dye_c':recipe.dye_c}

def formula_distance(p,q):
    return sum((p[k]-q[k])**2 for k in ('dye_a','dye_b','dye_c'))**.5

def get_slot(db,key,lock=True):
    q=select(ScheduleSlot).where(ScheduleSlot.id==key)
    slot=db.scalar(q.with_for_update() if lock else q)
    if not slot:raise HTTPException(404,'排产缸次不存在')
    return slot

def lock_machine(db,machine_id):
    machine=db.scalar(select(DyeMachine).where(DyeMachine.id==machine_id).with_for_update())
    if not machine:raise HTTPException(404,'染机不存在')
    return machine

def predecessor(db,machine_id,seq):
    return db.scalar(select(ScheduleSlot).where(ScheduleSlot.machine_id==machine_id,ScheduleSlot.seq<seq).order_by(ScheduleSlot.seq.desc()).limit(1))

def judge_transition(db,machine_id,prev_snap,next_snap):
    # 用历次免洗换色的前后配方与首测色差预测免洗超差风险；证据不足要求清洗。
    base={'machine_id':machine_id,'before':prev_snap,'after':next_snap,'tolerance':FORMULA_TOLERANCE,'evidence_min':EVIDENCE_MIN,'delta_e_limit':DELTA_E_LIMIT,'decided_at':datetime.utcnow().isoformat()+'Z'}
    if prev_snap is None:
        return {**base,'outcome':'no_transition','reason':'本机首缸，无换色过渡，无需清洗判定','evidence':[],'evidence_count':0,'inspection':False}
    depth_before=round(sum(prev_snap[k] for k in ('dye_a','dye_b','dye_c')),4)
    depth_after=round(sum(next_snap[k] for k in ('dye_a','dye_b','dye_c')),4)
    records=db.scalars(select(ColorChangeRecord).where(ColorChangeRecord.machine_id==machine_id,ColorChangeRecord.washed==False)).all()
    evidence=[{'record_id':r.id,'prev_code':r.prev_snapshot['code'],'next_code':r.next_snapshot['code'],'first_delta_e':r.first_delta_e,'prev_distance':round(formula_distance(r.prev_snapshot,prev_snap),3),'next_distance':round(formula_distance(r.next_snapshot,next_snap),3)} for r in records if formula_distance(r.prev_snapshot,prev_snap)<=FORMULA_TOLERANCE and formula_distance(r.next_snapshot,next_snap)<=FORMULA_TOLERANCE]
    base.update({'depth_before':depth_before,'depth_after':depth_after,'evidence':evidence,'evidence_count':len(evidence)})
    if len(evidence)<EVIDENCE_MIN:
        return {**base,'outcome':'wash_required','reason':f'同机免洗换色证据不足（{len(evidence)}/{EVIDENCE_MIN} 条），要求清洗','inspection':False}
    worst=max(e['first_delta_e'] for e in evidence)
    base['max_delta_e']=round(worst,3)
    if worst>DELTA_E_LIMIT:
        return {**base,'outcome':'wash_required','reason':f'历史免洗换色首测色差超差（最高 ΔE={worst:.2f}），串色风险高，要求清洗','inspection':False}
    return {**base,'outcome':'no_wash_ok','reason':f'{len(evidence)} 条同机免洗证据首测均合格，允许免洗，按染机留出首测检验','inspection':True}

def apply_judgment(db,slot,user):
    pred=predecessor(db,slot.machine_id,slot.seq)
    j=judge_transition(db,slot.machine_id,pred.recipe_snapshot if pred else None,slot.recipe_snapshot)
    j['prev_slot_id']=pred.id if pred else None
    j['prev_code']=pred.code if pred else None
    j['slot_id']=slot.id
    slot.judgment=j
    slot.inspection_reserved=bool(j.get('inspection'))
    event(db,slot.id,'judge',user,j)
    return j

def void_broken_vouchers(db,machine_ids,user,reason):
    # 清洗凭据只对当时的前后两缸有效：插单/改排改变相邻关系后，受影响凭据立即失效。
    vouchers=db.scalars(select(CleaningVoucher).where(CleaningVoucher.machine_id.in_(machine_ids),CleaningVoucher.state=='active')).all()
    for v in vouchers:
        nxt=db.get(ScheduleSlot,v.next_slot_id)
        pred=predecessor(db,nxt.machine_id,nxt.seq) if nxt else None
        if not nxt or nxt.machine_id!=v.machine_id or (pred.id if pred else None)!=v.prev_slot_id:
            v.state='void';v.void_reason=reason
            event(db,v.next_slot_id,'void',user,{'voucher_id':v.id,'pair':[v.prev_code,v.next_code],'reason':reason})

def create_slot(db,p,user):
    machine=lock_machine(db,p.machine_id)
    if db.scalar(select(ScheduleSlot).where(ScheduleSlot.code==p.code)):raise HTTPException(409,'排产缸号已存在')
    recipe=db.get(DyeRecipe,p.recipe_id)
    if not recipe:raise HTTPException(404,'配方不存在')
    if p.before_slot_id:
        anchor=db.scalar(select(ScheduleSlot).where(ScheduleSlot.id==p.before_slot_id,ScheduleSlot.machine_id==machine.id))
        if not anchor:raise HTTPException(409,'插单位置不在本机队列')
        seq=anchor.seq
        db.execute(update(ScheduleSlot).where(ScheduleSlot.machine_id==machine.id,ScheduleSlot.seq>=seq).values(seq=ScheduleSlot.seq+1))
    else:
        seq=(db.scalar(select(ScheduleSlot.seq).where(ScheduleSlot.machine_id==machine.id).order_by(ScheduleSlot.seq.desc()).limit(1)) or 0)+1
    slot=ScheduleSlot(machine_id=machine.id,code=p.code,recipe_id=recipe.id,recipe_snapshot=snapshot_of(recipe),kg=p.kg,seq=seq,created_by=user.email)
    db.add(slot);db.flush()
    judgment=apply_judgment(db,slot,user)
    void_broken_vouchers(db,[machine.id],user,'插单导致前后缸变化，清洗凭据失效')
    event(db,slot.id,'plan',user,{'code':slot.code,'machine':machine.code,'seq':seq,'inserted':bool(p.before_slot_id),'outcome':judgment['outcome']})
    log(db,user,f'排产 {slot.code} 上机 {machine.code} 顺位{seq} 判定{judgment["outcome"]}')
    db.commit();return slot

def reschedule(db,key,p,user):
    slot=get_slot(db,key)
    if slot.state!='planned':raise HTTPException(409,'已开染缸次留在原机，不能改排')
    ids=sorted({slot.machine_id,p.machine_id})
    machines={m.id:m for m in db.scalars(select(DyeMachine).where(DyeMachine.id.in_(ids)).order_by(DyeMachine.id).with_for_update())}
    if p.machine_id not in machines:raise HTTPException(404,'染机不存在')
    old={'machine':machines[slot.machine_id].code,'seq':slot.seq}
    if p.before_slot_id:
        if p.before_slot_id==slot.id:raise HTTPException(409,'不能以自身为插位锚点')
        anchor=db.scalar(select(ScheduleSlot).where(ScheduleSlot.id==p.before_slot_id,ScheduleSlot.machine_id==p.machine_id))
        if not anchor:raise HTTPException(409,'插位锚点不在目标机队列')
        seq=anchor.seq
        db.execute(update(ScheduleSlot).where(ScheduleSlot.machine_id==p.machine_id,ScheduleSlot.seq>=seq,ScheduleSlot.id!=slot.id).values(seq=ScheduleSlot.seq+1))
    else:
        seq=(db.scalar(select(ScheduleSlot.seq).where(ScheduleSlot.machine_id==p.machine_id,ScheduleSlot.id!=slot.id).order_by(ScheduleSlot.seq.desc()).limit(1)) or 0)+1
    slot.machine_id=p.machine_id;slot.seq=seq;db.flush()
    void_broken_vouchers(db,ids,user,'改排导致前后缸变化，清洗凭据失效')
    event(db,slot.id,'reschedule',user,{'code':slot.code,'from':old,'to':{'machine':machines[p.machine_id].code,'seq':seq}})
    log(db,user,f'改排 {slot.code} {old["machine"]}顺位{old["seq"]} → {machines[p.machine_id].code}顺位{seq}')
    db.commit();return slot

def rejudge(db,key,user):
    slot=get_slot(db,key)
    if slot.state!='planned':raise HTTPException(409,'仅待排缸次可重算判定')
    lock_machine(db,slot.machine_id)
    j=apply_judgment(db,slot,user)
    log(db,user,f'重算判定 {slot.code} → {j["outcome"]}')
    db.commit();return slot

def confirm_wash(db,p,user):
    slot=get_slot(db,p.slot_id)
    if slot.state!='planned':raise HTTPException(409,'缸次已开染，清洗凭据不再受理')
    lock_machine(db,slot.machine_id)
    pred=predecessor(db,slot.machine_id,slot.seq)
    j=slot.judgment or {}
    if j.get('prev_slot_id','-')!=(pred.id if pred else None):raise HTTPException(409,'判定已失效，请先重算再确认清洗')
    if j.get('outcome')!='wash_required':raise HTTPException(409,'当前判定未要求清洗，无需凭据')
    if db.scalar(select(CleaningVoucher).where(CleaningVoucher.next_slot_id==slot.id,CleaningVoucher.state=='active')):raise HTTPException(409,'该缸已有有效清洗凭据，不可重复确认')
    voucher=CleaningVoucher(machine_id=slot.machine_id,prev_slot_id=pred.id,next_slot_id=slot.id,prev_code=pred.code,next_code=slot.code,confirmed_by=user.email)
    db.add(voucher);db.flush()
    event(db,slot.id,'wash',user,{'voucher_id':voucher.id,'pair':[voucher.prev_code,voucher.next_code],'confirmed_by':user.email})
    log(db,user,f'确认清洗 {voucher.prev_code}→{voucher.next_code} 凭据#{voucher.id}')
    db.commit();return voucher

def block(db,slot,user,reason):
    # 拦截原因落库，供排产页面回看。
    event(db,slot.id,'block',user,{'code':slot.code,'reason':reason})
    log(db,user,f'拦截开染 {slot.code}：{reason}')
    db.commit()
    raise HTTPException(409,reason)

def start_slot(db,key,p,user):
    slot=get_slot(db,key)
    request_key=p.request_key or f'start-{slot.id}'
    if slot.state=='started' and slot.start_key==request_key:
        return slot,'replayed'  # 写入中断后的重试：直接返回原结果，不重复核销清洗凭据
    if slot.state!='planned':raise HTTPException(409,'缸次已开染或已完工')
    lock_machine(db,slot.machine_id)
    head=db.scalar(select(ScheduleSlot).where(ScheduleSlot.machine_id==slot.machine_id,ScheduleSlot.state=='planned').order_by(ScheduleSlot.seq).limit(1))
    if not head or head.id!=slot.id:block(db,slot,user,'仅本机队列最前的待排缸可开染')
    busy=db.scalar(select(ScheduleSlot).where(ScheduleSlot.machine_id==slot.machine_id,ScheduleSlot.state=='started').limit(1))
    if busy:block(db,slot,user,f'上缸 {busy.code} 尚未完工，染机占用中')
    pred=predecessor(db,slot.machine_id,slot.seq)
    j=slot.judgment or {}
    if j.get('prev_slot_id','-')!=(pred.id if pred else None):
        block(db,slot,user,'插单或改排后判定失效，重算前禁止开染')
    # 开染以同机实际完工的上一缸为准
    prev_done=db.scalar(select(ScheduleSlot).where(ScheduleSlot.machine_id==slot.machine_id,ScheduleSlot.state=='completed').order_by(ScheduleSlot.completed_at.desc(),ScheduleSlot.seq.desc()).limit(1))
    if (prev_done.id if prev_done else None)!=(pred.id if pred else None):
        block(db,slot,user,'上一缸以同机实际完工为准，与判定依据不一致，请重算')
    voucher=None
    if j.get('outcome')=='wash_required':
        voucher=db.scalar(select(CleaningVoucher).where(CleaningVoucher.next_slot_id==slot.id,CleaningVoucher.state=='active',CleaningVoucher.prev_slot_id==j.get('prev_slot_id')).with_for_update())
        if not voucher:block(db,slot,user,'判定要求清洗，缺少有效清洗凭据')
        voucher.state='used';voucher.used_key=request_key;voucher.used_at=datetime.utcnow()
    slot.state='started';slot.start_key=request_key;slot.started_at=datetime.utcnow()
    event(db,slot.id,'start',user,{'code':slot.code,'machine_id':slot.machine_id,'prev_slot_id':j.get('prev_slot_id'),'prev_code':j.get('prev_code'),'outcome':j.get('outcome'),'voucher_id':voucher.id if voucher else None,'request_key':request_key})
    log(db,user,f'开染 {slot.code} 判定{j.get("outcome")}'+(f' 核销凭据#{voucher.id}' if voucher else ''))
    db.commit();return slot,'started'

def complete_slot(db,key,p,user):
    slot=get_slot(db,key)
    if slot.state!='started':raise HTTPException(409,'仅已开染缸次可登记完工')
    lock_machine(db,slot.machine_id)
    slot.state='completed';slot.completed_at=datetime.utcnow()
    prev_done=db.scalar(select(ScheduleSlot).where(ScheduleSlot.machine_id==slot.machine_id,ScheduleSlot.state=='completed',ScheduleSlot.id!=slot.id).order_by(ScheduleSlot.completed_at.desc(),ScheduleSlot.seq.desc()).limit(1))
    record=None
    if prev_done:
        used=db.scalar(select(CleaningVoucher).where(CleaningVoucher.next_slot_id==slot.id,CleaningVoucher.state=='used'))
        record=ColorChangeRecord(machine_id=slot.machine_id,prev_snapshot=prev_done.recipe_snapshot,next_snapshot=slot.recipe_snapshot,washed=bool(used),first_delta_e=p.first_delta_e,source='auto',slot_id=slot.id,note=f'完工自动登记 {prev_done.code}→{slot.code}',recorded_by=user.email)
        db.add(record);db.flush()
    event(db,slot.id,'complete',user,{'code':slot.code,'first_delta_e':p.first_delta_e,'prev_code':prev_done.code if prev_done else None,'washed':bool(record and record.washed),'record_id':record.id if record else None})
    log(db,user,f'完工 {slot.code} 首测ΔE={p.first_delta_e}'+(f' 生成换色记录#{record.id}' if record else ''))
    db.commit();return slot

def register_history(db,p,user):
    machine=db.get(DyeMachine,p.machine_id)
    if not machine:raise HTTPException(404,'染机不存在')
    prev_recipe=db.get(DyeRecipe,p.prev_recipe_id);next_recipe=db.get(DyeRecipe,p.next_recipe_id)
    if not prev_recipe or not next_recipe:raise HTTPException(404,'前后配方不存在')
    if prev_recipe.id==next_recipe.id:raise HTTPException(409,'前后配方须为不同配方')
    record=ColorChangeRecord(machine_id=machine.id,prev_snapshot=snapshot_of(prev_recipe),next_snapshot=snapshot_of(next_recipe),washed=p.washed,first_delta_e=p.first_delta_e,source='manual',note=p.note,recorded_by=user.email)
    db.add(record);db.flush()
    event(db,None,'history',user,{'record_id':record.id,'machine':machine.code,'pair':[prev_recipe.code,next_recipe.code],'washed':p.washed,'first_delta_e':p.first_delta_e})
    log(db,user,f'登记历史换色 {machine.code} {prev_recipe.code}→{next_recipe.code} ΔE={p.first_delta_e}')
    db.commit();return record
