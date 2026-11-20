from fastapi import APIRouter,Depends
from sqlalchemy import select
from .database import session
from .auth import current,editor,admin
from .fulfillment_models import DyeLot,DyeIssue,ColorDispatch,ShadeComplaint
from .fulfillment_schemas import LotInput,LotStateInput,IssueInput,DispatchInput,ReceiptInput,ConclusionInput,ComplaintInput,DecisionInput,RemakeInput,ComplaintCloseInput
from . import stock_service,dispatch_service,complaint_service
router=APIRouter()
@router.get('/dye-lots')
def lots(user=Depends(current),db=Depends(session)):return db.scalars(select(DyeLot).order_by(DyeLot.id.desc())).all()
@router.post('/dye-lots')
def receive(p:LotInput,user=Depends(editor),db=Depends(session)):return stock_service.receive(db,p,user)
@router.put('/dye-lots/{key}/state')
def state(key:int,p:LotStateInput,user=Depends(admin),db=Depends(session)):return stock_service.set_state(db,key,p,user)
@router.get('/dye-issues')
def issues(user=Depends(current),db=Depends(session)):return db.scalars(select(DyeIssue).order_by(DyeIssue.id.desc())).all()
@router.post('/dye-issues')
def issue(p:IssueInput,user=Depends(editor),db=Depends(session)):return stock_service.issue(db,p,user)
@router.get('/color-dispatches')
def dispatches(user=Depends(current),db=Depends(session)):return db.scalars(select(ColorDispatch).order_by(ColorDispatch.id.desc())).all()
@router.post('/color-dispatches')
def dispatch(p:DispatchInput,user=Depends(editor),db=Depends(session)):return dispatch_service.create(db,p,user)
@router.post('/color-dispatches/{key}/receive')
def receive_dispatch(key:int,p:ReceiptInput,user=Depends(editor),db=Depends(session)):return dispatch_service.receive(db,key,p,user)
@router.post('/color-dispatches/{key}/conclusion')
def conclude(key:int,p:ConclusionInput,user=Depends(editor),db=Depends(session)):return dispatch_service.conclude(db,key,p,user)
@router.get('/shade-complaints')
def complaints(user=Depends(current),db=Depends(session)):return db.scalars(select(ShadeComplaint).order_by(ShadeComplaint.id.desc())).all()
@router.post('/shade-complaints')
def complaint(p:ComplaintInput,user=Depends(editor),db=Depends(session)):return complaint_service.create(db,p,user)
@router.post('/shade-complaints/{key}/decision')
def decide(key:int,p:DecisionInput,user=Depends(admin),db=Depends(session)):return complaint_service.decide(db,key,p,user)
@router.post('/shade-complaints/{key}/remake')
def remake(key:int,p:RemakeInput,user=Depends(editor),db=Depends(session)):return complaint_service.remake(db,key,p,user)
@router.post('/shade-complaints/{key}/close')
def close(key:int,p:ComplaintCloseInput,user=Depends(admin),db=Depends(session)):return complaint_service.close(db,key,p,user)
