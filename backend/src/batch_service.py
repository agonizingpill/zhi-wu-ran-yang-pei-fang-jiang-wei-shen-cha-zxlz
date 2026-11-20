from fastapi import HTTPException
from sqlalchemy import select
from .models import Trial,Swatch,DyeRecipe
from .production_models import DyeBatch
from .recipe_service import log

def create_batch(db,data,user,commit=True):
    trial=db.get(Trial,data.approved_trial_id)
    if not trial:raise HTTPException(404,'复染试验不存在')
    if trial.state!='approved' or not db.get(DyeRecipe,trial.recipe_id).locked:raise HTTPException(409,'仅已批准且配方冻结的复染试验可下生产缸次')
    if db.scalar(select(DyeBatch.id).where(DyeBatch.code==data.code)):raise HTTPException(409,'生产缸号已存在')
    target=db.get(Swatch,trial.reference_swatch_id)
    recipe=db.get(DyeRecipe,trial.recipe_id)
    batch=DyeBatch(**data.model_dump(),target_snapshot={'lot':target.lot,'recipe_id':trial.recipe_id,'l':target.l,'a':target.a,'b':target.b,'trial_delta_e':trial.delta_e,'recipe_snapshot':{k:getattr(recipe,k) for k in ['id','code','name','dye_a','dye_b','dye_c']}})
    db.add(batch);log(db,user,f'下生产缸 {data.code} {data.kg}kg');db.flush()
    if commit:db.commit()
    return batch

def get_batch(db,key):
    batch=db.scalar(select(DyeBatch).where(DyeBatch.id==key).with_for_update())
    if not batch:raise HTTPException(404,'生产缸次不存在')
    return batch

def measure_batch(db,key,data,user):
    batch=get_batch(db,key)
    if batch.state=='released':raise HTTPException(409,'已放行缸次实测值冻结')
    for k,v in data.model_dump().items():setattr(batch,k,v)
    batch.delta_e=sum((getattr(batch,'lab_'+k)-batch.target_snapshot[k])**2 for k in ['l','a','b'])**.5
    batch.state='hold' if batch.delta_e>3 else 'qualified'
    log(db,user,f'生产缸 {batch.code} 实测ΔE={batch.delta_e:.3f} {batch.state}');db.commit();return batch

def release_batch(db,key,user):
    batch=get_batch(db,key)
    if batch.state!='qualified' or batch.delta_e is None or batch.delta_e>3:raise HTTPException(409,'缸次尚未合格、超色差或已放行，不能签放')
    from .stock_service import release_guard
    release_guard(db,batch)
    batch.state='released';batch.released_by=user.email
    log(db,user,f'签放生产缸 {batch.code}');db.commit();return batch
