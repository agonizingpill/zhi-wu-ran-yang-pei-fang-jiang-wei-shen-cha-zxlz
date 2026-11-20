from fastapi import HTTPException
from sqlalchemy import select
from .models import DyeRecipe,Swatch,Trial,Audit
from .constants import TrialState

def log(db,user,action):db.add(Audit(actor=user.email,action=action))
def require(db,model,key):
    item=db.get(model,key)
    if not item:raise HTTPException(404,'领域记录不存在')
    return item

def save_recipe(db,data,user,key=None):
    if key:
        from .revision_service import revision_edit_guard
        revision_edit_guard(db,key)
        item=require(db,DyeRecipe,key)
        if item.locked:raise HTTPException(409,'该配方已冻结；请创建修订配方后再调浓度')
        other=db.scalar(select(DyeRecipe).where(DyeRecipe.code==data.code,DyeRecipe.id!=key))
    else:
        other=db.scalar(select(DyeRecipe).where(DyeRecipe.code==data.code));item=DyeRecipe()
    if other:raise HTTPException(409,'配方编号已存在')
    for k,v in data.model_dump().items():setattr(item,k,v)
    db.add(item);log(db,user,f'保存配方 {data.code}');db.commit();return item

def create_swatch(db,data,user):
    recipe=require(db,DyeRecipe,data.recipe_id)
    from .revision_service import revision_edit_guard
    revision_edit_guard(db,recipe.id)
    if recipe.locked:raise HTTPException(409,'冻结配方不可追加试样，请创建修订配方')
    if db.scalar(select(Swatch).where(Swatch.lot==data.lot)):raise HTTPException(409,'染样批号已存在')
    item=Swatch(**data.model_dump());db.add(item);log(db,user,f'登记染样 {data.lot}');db.commit();return item

def create_trial(db,data,user):
    recipe=require(db,DyeRecipe,data.recipe_id)
    from .revision_service import revision_edit_guard
    revision_edit_guard(db,recipe.id)
    if recipe.locked:raise HTTPException(409,'该配方已有放行试验，不能再次签批')
    ref=require(db,Swatch,data.reference_swatch_id);candidate=require(db,Swatch,data.candidate_swatch_id)
    if ref.id==candidate.id:raise HTTPException(409,'目标与候选必须是不同染样')
    if ref.recipe_id!=recipe.id or candidate.recipe_id!=recipe.id:raise HTTPException(409,'染样不属于同一配方')
    delta=sum((getattr(ref,k)-getattr(candidate,k))**2 for k in ['l','a','b'])**.5
    item=Trial(**data.model_dump(),delta_e=delta,state=TrialState.DRAFT)
    db.add(item);log(db,user,f'建立复染试验 ΔE={delta:.3f}');db.commit();return item

def transition(db,key,action,user):
    item=require(db,Trial,key)
    if action=='verify':
        if item.state!='draft':raise HTTPException(409,'仅草稿试验可确认')
        if item.delta_e>3:
            item.state='rejected';item.note='色差超 3，退回修色';log(db,user,'色差超限退回');db.commit();return item
        item.state='verified'
    elif action=='approve':
        if item.delta_e>3:raise HTTPException(409,'ΔE > 3，不能批准复染')
        if item.state!='verified':raise HTTPException(409,'需调色师先确认色差')
        recipe=require(db,DyeRecipe,item.recipe_id)
        if recipe.locked:raise HTTPException(409,'该配方已冻结')
        recipe.locked=True;item.state='approved'
    log(db,user,f'复染 {key} {action}');db.commit();return item
