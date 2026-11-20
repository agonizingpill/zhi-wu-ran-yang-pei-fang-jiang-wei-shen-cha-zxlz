from fastapi import HTTPException
from sqlalchemy import select
from .models import DyeRecipe
from .production_models import RecipeRevision
from .recipe_service import log

def create_revision(db,data,user):
    parent=db.scalar(select(DyeRecipe).where(DyeRecipe.id==data.parent_recipe_id).with_for_update())
    if not parent:raise HTTPException(404,'父配方不存在')
    if not parent.locked:raise HTTPException(409,'只为已冻结配方建立修订，未冻结配方请直接编辑')
    if db.scalar(select(DyeRecipe.id).where(DyeRecipe.code==data.child_code)):raise HTTPException(409,'子配方编号已存在，不得复用现有版本或建立循环')
    child=DyeRecipe(code=data.child_code,name=data.child_name,dye_a=parent.dye_a,dye_b=parent.dye_b,dye_c=parent.dye_c,locked=False)
    db.add(child);db.flush()
    revision=RecipeRevision(parent_recipe_id=parent.id,child_recipe_id=child.id,reason=data.reason,parent_snapshot={k:getattr(parent,k)for k in ['code','name','dye_a','dye_b','dye_c','locked']})
    db.add(revision);log(db,user,f'建立修订 {parent.code} → {child.code}');db.commit();return revision

def review_revision(db,key,user):
    revision=db.scalar(select(RecipeRevision).where(RecipeRevision.id==key).with_for_update())
    if not revision:raise HTTPException(404,'修订不存在')
    if revision.state!='pending':raise HTTPException(409,'已审修订不得重复审核')
    parent=db.get(DyeRecipe,revision.parent_recipe_id);child=db.get(DyeRecipe,revision.child_recipe_id)
    if not parent.locked or child.locked:raise HTTPException(409,'父子版本状态已变化，不能审核')
    revision.state='approved';revision.reviewed_by=user.email
    log(db,user,f'审核修订来源 {parent.code} → {child.code}');db.commit();return revision

def revision_edit_guard(db,recipe_id):
    rev=db.scalar(select(RecipeRevision).where(RecipeRevision.child_recipe_id==recipe_id))
    if rev and rev.state!='approved':raise HTTPException(409,'修订来源尚未审核，不能调整浓度或建立试样')
