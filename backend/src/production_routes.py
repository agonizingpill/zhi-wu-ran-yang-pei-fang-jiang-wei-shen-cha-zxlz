from fastapi import APIRouter,Depends
from sqlalchemy import select
from .database import session
from .auth import current,editor,admin
from .production_models import RecipeRevision,DyeBatch
from .production_schemas import RevisionInput,BatchInput,BatchMeasurement
from .revision_service import create_revision,review_revision
from .batch_service import create_batch,measure_batch,release_batch
router=APIRouter()
@router.get('/revisions')
def revisions(user=Depends(current),db=Depends(session)):return db.scalars(select(RecipeRevision).order_by(RecipeRevision.id.desc())).all()
@router.post('/revisions')
def add_revision(data:RevisionInput,user=Depends(editor),db=Depends(session)):return create_revision(db,data,user)
@router.post('/revisions/{key}/review')
def review(key:int,user=Depends(admin),db=Depends(session)):return review_revision(db,key,user)
@router.get('/batches')
def batches(user=Depends(current),db=Depends(session)):return db.scalars(select(DyeBatch).order_by(DyeBatch.id.desc())).all()
@router.post('/batches')
def add_batch(data:BatchInput,user=Depends(editor),db=Depends(session)):return create_batch(db,data,user)
@router.put('/batches/{key}/measurement')
def measure(key:int,data:BatchMeasurement,user=Depends(editor),db=Depends(session)):return measure_batch(db,key,data,user)
@router.post('/batches/{key}/release')
def release(key:int,user=Depends(admin),db=Depends(session)):return release_batch(db,key,user)
