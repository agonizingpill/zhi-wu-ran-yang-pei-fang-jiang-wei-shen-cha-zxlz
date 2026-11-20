from datetime import datetime
from sqlalchemy import select
from fastapi import HTTPException
from .fulfillment_models import ColorDispatch
from .batch_service import get_batch
from .stock_service import recipe_snapshot
from .recipe_service import log

def get_dispatch(db,key,lock=True):
    q=select(ColorDispatch).where(ColorDispatch.id==key)
    item=db.scalar(q.with_for_update() if lock else q)
    if not item:raise HTTPException(404,'客户发样单不存在')
    return item

def create(db,p,user):
    batch=get_batch(db,p.batch_id)
    if batch.state!='released':raise HTTPException(409,'只有已签放生产缸次可以发客户色样')
    if db.scalar(select(ColorDispatch).where((ColorDispatch.batch_id==batch.id)|(ColorDispatch.tracking==p.tracking))):raise HTTPException(409,'该缸已发样或运单号重复')
    snapshot={'batch_code':batch.code,'batch_kg':batch.kg,'approved_trial_id':batch.approved_trial_id,'lab_l':batch.lab_l,'lab_a':batch.lab_a,'lab_b':batch.lab_b,'delta_e':batch.delta_e,'target':dict(batch.target_snapshot),'recipe':recipe_snapshot(db,batch),'released_by':batch.released_by}
    item=ColorDispatch(**p.model_dump(),snapshot=snapshot,sent_by=user.email);db.add(item);log(db,user,f'客户发样 {batch.code} {p.customer} 运单{p.tracking}');db.commit();return item

def receive(db,key,p,user):
    item=get_dispatch(db,key)
    if item.state!='sent':raise HTTPException(409,'发样已签收，不能重复签收或改收件人')
    item.received_by=p.received_by;item.received_at=datetime.utcnow();item.state='received'
    log(db,user,f'客户色样签收 {item.tracking} 收件人{p.received_by}');db.commit();return item

def conclude(db,key,p,user):
    item=get_dispatch(db,key)
    if p.batch_id!=item.batch_id:raise HTTPException(409,'客户结论与发样缸次不一致')
    if item.state!='received':raise HTTPException(409,'须客户签收后录结论，已有结论不可重复改写')
    item.state=p.conclusion;item.conclusion_note=p.note;log(db,user,f'客户色样结论 {item.tracking} {p.conclusion}');db.commit();return item
