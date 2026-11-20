from sqlalchemy import String,Float,ForeignKey,JSON,CheckConstraint,DateTime,func
from sqlalchemy.orm import Mapped,mapped_column
from .database import Base
class RecipeRevision(Base):
    __tablename__='recipe_revisions'
    __table_args__=(CheckConstraint('parent_recipe_id <> child_recipe_id'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    parent_recipe_id:Mapped[int]=mapped_column(ForeignKey('dye_recipes.id'))
    child_recipe_id:Mapped[int]=mapped_column(ForeignKey('dye_recipes.id'),unique=True)
    reason:Mapped[str]=mapped_column(String(300))
    parent_snapshot:Mapped[dict]=mapped_column(JSON)
    state:Mapped[str]=mapped_column(String(20),default='pending')
    reviewed_by:Mapped[str]=mapped_column(String(120),default='')
    created_at:Mapped[object]=mapped_column(DateTime,server_default=func.now())
class DyeBatch(Base):
    __tablename__='dye_batches'
    __table_args__=(CheckConstraint('kg>0'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    code:Mapped[str]=mapped_column(String(50),unique=True)
    approved_trial_id:Mapped[int]=mapped_column(ForeignKey('trials.id'))
    kg:Mapped[float]=mapped_column(Float)
    target_snapshot:Mapped[dict]=mapped_column(JSON)
    lab_l:Mapped[float|None]=mapped_column(Float,nullable=True)
    lab_a:Mapped[float|None]=mapped_column(Float,nullable=True)
    lab_b:Mapped[float|None]=mapped_column(Float,nullable=True)
    delta_e:Mapped[float|None]=mapped_column(Float,nullable=True)
    state:Mapped[str]=mapped_column(String(20),default='planned')
    released_by:Mapped[str]=mapped_column(String(120),default='')
