from sqlalchemy import String,Float,Boolean,ForeignKey,JSON,CheckConstraint,DateTime,func
from sqlalchemy.orm import Mapped,mapped_column
from .database import Base
class User(Base):
    __tablename__='users'
    id:Mapped[int]=mapped_column(primary_key=True)
    email:Mapped[str]=mapped_column(String(120),unique=True)
    password:Mapped[str]=mapped_column(String(240))
    role:Mapped[str]=mapped_column(String(20))
class DyeRecipe(Base):
    __tablename__='dye_recipes'
    __table_args__=(CheckConstraint('dye_a>=0 AND dye_b>=0 AND dye_c>=0'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    code:Mapped[str]=mapped_column(String(40),unique=True)
    name:Mapped[str]=mapped_column(String(100))
    dye_a:Mapped[float]=mapped_column(Float)
    dye_b:Mapped[float]=mapped_column(Float)
    dye_c:Mapped[float]=mapped_column(Float)
    locked:Mapped[bool]=mapped_column(Boolean,default=False)
class Swatch(Base):
    __tablename__='swatches'
    __table_args__=(CheckConstraint('l>=0 AND l<=100'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    recipe_id:Mapped[int]=mapped_column(ForeignKey('dye_recipes.id'))
    lot:Mapped[str]=mapped_column(String(60),unique=True)
    spectrum:Mapped[list]=mapped_column(JSON)
    l:Mapped[float]=mapped_column(Float)
    a:Mapped[float]=mapped_column(Float)
    b:Mapped[float]=mapped_column(Float)
    measured:Mapped[bool]=mapped_column(Boolean,default=True)
class Trial(Base):
    __tablename__='trials'
    id:Mapped[int]=mapped_column(primary_key=True)
    recipe_id:Mapped[int]=mapped_column(ForeignKey('dye_recipes.id'))
    reference_swatch_id:Mapped[int]=mapped_column(ForeignKey('swatches.id'))
    candidate_swatch_id:Mapped[int]=mapped_column(ForeignKey('swatches.id'))
    delta_e:Mapped[float]=mapped_column(Float)
    state:Mapped[str]=mapped_column(String(20),default='draft')
    note:Mapped[str]=mapped_column(String(240),default='')
class Audit(Base):
    __tablename__='audits'
    id:Mapped[int]=mapped_column(primary_key=True)
    actor:Mapped[str]=mapped_column(String(120))
    action:Mapped[str]=mapped_column(String(180))
    at:Mapped[object]=mapped_column(DateTime,server_default=func.now())
