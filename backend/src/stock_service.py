from datetime import date
from sqlalchemy import select
from fastapi import HTTPException
from .models import Trial,DyeRecipe
from .fulfillment_models import DyeLot,DyeIssue
from .batch_service import get_batch
from .recipe_service import log,require

def recipe_snapshot(db,batch):
    if 'recipe_snapshot' in batch.target_snapshot:return dict(batch.target_snapshot['recipe_snapshot'])
    trial=require(db,Trial,batch.approved_trial_id);recipe=require(db,DyeRecipe,trial.recipe_id)
    return {k:getattr(recipe,k) for k in ['id','code','name','dye_a','dye_b','dye_c']}

def receive(db,p,user):
    if p.expires_on<date.today():raise HTTPException(409,'新入库批次不能已过期')
    if db.scalar(select(DyeLot).where(DyeLot.code==p.code)):raise HTTPException(409,'染料批号已存在')
    lot=DyeLot(**p.model_dump());db.add(lot);log(db,user,f'染料入库 {p.code} {p.component} {p.available_kg}kg');db.commit();return lot

def set_state(db,key,p,user):
    lot=db.scalar(select(DyeLot).where(DyeLot.id==key).with_for_update())
    if not lot:raise HTTPException(404,'染料批次不存在')
    if lot.state==p.state:raise HTTPException(409,'批次已处于该状态')
    lot.state=p.state;log(db,user,f'染料 {lot.code} 状态{p.state}');db.commit();return lot

def issue(db,p,user):
    batch=get_batch(db,p.batch_id)
    if batch.state=='released':raise HTTPException(409,'已签放历史缸次不能追加称料')
    if db.scalar(select(DyeIssue).where(DyeIssue.batch_id==batch.id)):raise HTTPException(409,'该缸已整单领料，不可重复扣减')
    ids=[p.lot_a_id,p.lot_b_id,p.lot_c_id]
    if len(set(ids))!=3:raise HTTPException(409,'三个组分必须选择对应的独立批次')
    lots={x.id:x for x in db.scalars(select(DyeLot).where(DyeLot.id.in_(ids)).order_by(DyeLot.id).with_for_update())}
    if len(lots)!=3:raise HTTPException(404,'染料批次不存在')
    snapshot=recipe_snapshot(db,batch);allocations=[]
    # Validate all three components before mutating any balance. The batch and
    # ordered lot locks protect the complete A/B/C transaction from duplicate issues.
    for component,lot_id in zip('ABC',ids):
        lot=lots[lot_id];kg=round(snapshot['dye_'+component.lower()]*batch.kg/100,6)
        if lot.component!=component:raise HTTPException(409,'染料批次组分不匹配')
        if lot.state!='active' or lot.expires_on<date.today():raise HTTPException(409,f'{component}组分已隔离或过期，整单未扣减')
        if lot.available_kg+1e-8<kg:raise HTTPException(409,f'{component}组分库存不足，整单未扣减')
        allocations.append((component,lot,kg))
    result=[]
    for component,lot,kg in allocations:
        lot.available_kg=round(lot.available_kg-kg,6)
        item=DyeIssue(batch_id=batch.id,lot_id=lot.id,component=component,kg=kg,recipe_snapshot=snapshot,issued_by=user.email);db.add(item);result.append(item)
    log(db,user,f'整单称料 {batch.code} A/B/C已按配方扣库存');db.commit();return result

def release_guard(db,batch):
    issues=db.scalars(select(DyeIssue).where(DyeIssue.batch_id==batch.id)).all()
    if len(issues)!=3 or {x.component for x in issues}!={'A','B','C'}:raise HTTPException(409,'新签放操作须完成A/B/C整单称料领用')
