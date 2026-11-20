from fastapi import APIRouter,Depends
from sqlalchemy import select
from .database import session
from .auth import current,editor,admin
from .schedule_models import DyeMachine,ScheduleSlot,ColorChangeRecord,CleaningVoucher,ScheduleEvent
from .schedule_schemas import SlotInput,RescheduleInput,StartInput,CompleteInput,HistoryInput,WashInput
from . import schedule_service as svc
router=APIRouter()

@router.get('/schedule/machines')
def machines(user=Depends(current),db=Depends(session)):
    rows=db.scalars(select(DyeMachine).order_by(DyeMachine.id)).all()
    slots=db.scalars(select(ScheduleSlot)).all()
    return [{'id':m.id,'code':m.code,'name':m.name,
             'queued':sum(1 for s in slots if s.machine_id==m.id and s.state=='planned'),
             'running':sum(1 for s in slots if s.machine_id==m.id and s.state=='started'),
             'inspection_reserved':sum(1 for s in slots if s.machine_id==m.id and s.inspection_reserved and s.state in ('planned','started'))} for m in rows]

@router.get('/schedule/slots')
def slots(user=Depends(current),db=Depends(session)):
    rows=db.scalars(select(ScheduleSlot).order_by(ScheduleSlot.machine_id,ScheduleSlot.seq)).all()
    by_machine={}
    for s in rows:by_machine.setdefault(s.machine_id,[]).append(s)
    out=[]
    for s in rows:
        peers=by_machine[s.machine_id];pred=peers[peers.index(s)-1] if peers.index(s)>0 else None
        current_prev_id=pred.id if pred else None
        judged_prev=(s.judgment or {}).get('prev_slot_id')
        out.append({'id':s.id,'machine_id':s.machine_id,'code':s.code,'recipe_id':s.recipe_id,'recipe_snapshot':s.recipe_snapshot,'kg':s.kg,'seq':s.seq,'state':s.state,'judgment':s.judgment,'inspection_reserved':s.inspection_reserved,'start_key':s.start_key,'started_at':s.started_at,'completed_at':s.completed_at,'created_by':s.created_by,'created_at':s.created_at,
                    'current_prev_id':current_prev_id,'current_prev_code':pred.code if pred else None,
                    'stale':s.state=='planned' and judged_prev!=current_prev_id})
    return out

@router.post('/schedule/slots')
def plan(p:SlotInput,user=Depends(editor),db=Depends(session)):return svc.create_slot(db,p,user)
@router.post('/schedule/slots/{key}/reschedule')
def reschedule(key:int,p:RescheduleInput,user=Depends(editor),db=Depends(session)):return svc.reschedule(db,key,p,user)
@router.post('/schedule/slots/{key}/rejudge')
def rejudge(key:int,user=Depends(editor),db=Depends(session)):return svc.rejudge(db,key,user)
@router.post('/schedule/slots/{key}/start')
def start(key:int,p:StartInput,user=Depends(editor),db=Depends(session)):
    slot,result=svc.start_slot(db,key,p,user)
    return {'slot_id':slot.id,'code':slot.code,'state':slot.state,'result':result}
@router.post('/schedule/slots/{key}/complete')
def complete(key:int,p:CompleteInput,user=Depends(editor),db=Depends(session)):return svc.complete_slot(db,key,p,user)
@router.get('/schedule/history')
def history(user=Depends(current),db=Depends(session)):return db.scalars(select(ColorChangeRecord).order_by(ColorChangeRecord.id.desc())).all()
@router.post('/schedule/history')
def add_history(p:HistoryInput,user=Depends(editor),db=Depends(session)):return svc.register_history(db,p,user)
@router.get('/schedule/vouchers')
def vouchers(user=Depends(current),db=Depends(session)):return db.scalars(select(CleaningVoucher).order_by(CleaningVoucher.id.desc())).all()
@router.post('/schedule/vouchers')
def wash(p:WashInput,user=Depends(admin),db=Depends(session)):return svc.confirm_wash(db,p,user)
@router.get('/schedule/events')
def events(user=Depends(current),db=Depends(session)):return db.scalars(select(ScheduleEvent).order_by(ScheduleEvent.id.desc()).limit(120)).all()
