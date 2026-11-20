from sqlalchemy import select
from fastapi import HTTPException
from .models import Trial,Swatch
from .production_models import DyeBatch
from .production_schemas import BatchInput
from .fulfillment_models import ShadeComplaint,ColorDispatch
from .batch_service import create_batch,get_batch
from .dispatch_service import get_dispatch
from .recipe_service import log,require

def get_complaint(db,key):
    item=db.scalar(select(ShadeComplaint).where(ShadeComplaint.id==key).with_for_update())
    if not item:raise HTTPException(404,'色差客诉不存在')
    return item

def create(db,p,user):
    dispatch=get_dispatch(db,p.dispatch_id)
    if dispatch.state!='disputed' or not dispatch.received_by:raise HTTPException(409,'仅客户已签收且明确色差争议的发样单可以客诉')
    if p.requested_kg>dispatch.snapshot['batch_kg']:raise HTTPException(409,'补染申请重量不能超过原缸重量')
    if db.scalar(select(ShadeComplaint).where(ShadeComplaint.dispatch_id==dispatch.id)):raise HTTPException(409,'该争议发样已有客诉，不可重复')
    item=ShadeComplaint(**p.model_dump());db.add(item);log(db,user,f'色差客诉 发样{dispatch.tracking} 补染{p.requested_kg}kg');db.commit();return item

def decide(db,key,p,user):
    item=get_complaint(db,key)
    if item.state!='open':raise HTTPException(409,'客诉已裁定，不可重复裁定')
    item.state=p.decision;item.decision_note=p.note;item.decided_by=user.email
    log(db,user,f'客诉{key}裁定 {p.decision}');db.commit();return item

def remake(db,key,p,user):
    item=get_complaint(db,key)
    if item.state!='remake_approved' or item.remake_batch_id:raise HTTPException(409,'须主管批准补染，且只能关联一个新缸')
    dispatch=require(db,ColorDispatch,item.dispatch_id);original=require(db,DyeBatch,dispatch.batch_id)
    trial=db.scalar(select(Trial).where(Trial.id==p.approved_trial_id).with_for_update())
    if not trial:raise HTTPException(404,'新复染试验不存在')
    if trial.id==original.approved_trial_id or trial.state!='approved' or db.scalar(select(DyeBatch).where(DyeBatch.approved_trial_id==trial.id)):raise HTTPException(409,'补染须新的、未被生产缸使用的已批准复染试验')
    target=require(db,Swatch,trial.reference_swatch_id);original_target=dispatch.snapshot['target']
    if sum((getattr(target,k)-original_target[k])**2 for k in ['l','a','b'])**.5>3:raise HTTPException(409,'新试验目标色与客诉原目标不一致，请重新确认客户色样')
    batch=create_batch(db,BatchInput(code=p.code,approved_trial_id=trial.id,kg=item.requested_kg),user,commit=False)
    item.remake_batch_id=batch.id;item.state='remaking';log(db,user,f'客诉{key}关联补染新缸 {batch.code}');db.commit();return item

def close(db,key,p,user):
    item=get_complaint(db,key)
    if item.state!='remaking' or not item.remake_batch_id:raise HTTPException(409,'客诉尚无补染新缸或已经关闭')
    if p.batch_id!=item.remake_batch_id:raise HTTPException(409,'必须使用本客诉关联的新缸，不能使用原缸或他单')
    batch=get_batch(db,item.remake_batch_id)
    if batch.state!='released':raise HTTPException(409,'补染新缸须正常称料、色差实测并主管签放后关闭')
    item.state='closed';item.closed_by=user.email;log(db,user,f'关闭客诉{key} 补染缸{batch.code}已签放');db.commit();return item
