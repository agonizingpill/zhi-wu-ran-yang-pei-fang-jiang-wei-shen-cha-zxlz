from datetime import date,datetime
from sqlalchemy import String,Float,ForeignKey,JSON,Date,DateTime,CheckConstraint,UniqueConstraint,func
from sqlalchemy.orm import Mapped,mapped_column
from .database import Base
class DyeLot(Base):
    __tablename__='dye_lots'
    __table_args__=(CheckConstraint("component IN ('A','B','C') AND available_kg>=0"),)
    id:Mapped[int]=mapped_column(primary_key=True)
    code:Mapped[str]=mapped_column(String(50),unique=True)
    component:Mapped[str]=mapped_column(String(1))
    available_kg:Mapped[float]=mapped_column(Float)
    expires_on:Mapped[date]=mapped_column(Date)
    state:Mapped[str]=mapped_column(String(24),default='active')
class DyeIssue(Base):
    __tablename__='dye_issues'
    __table_args__=(UniqueConstraint('batch_id','component'),CheckConstraint("component IN ('A','B','C') AND kg>=0"))
    id:Mapped[int]=mapped_column(primary_key=True)
    batch_id:Mapped[int]=mapped_column(ForeignKey('dye_batches.id'))
    lot_id:Mapped[int]=mapped_column(ForeignKey('dye_lots.id'))
    component:Mapped[str]=mapped_column(String(1))
    kg:Mapped[float]=mapped_column(Float)
    recipe_snapshot:Mapped[dict]=mapped_column(JSON)
    issued_by:Mapped[str]=mapped_column(String(120))
    issued_at:Mapped[datetime]=mapped_column(DateTime,server_default=func.now())
class ColorDispatch(Base):
    __tablename__='color_dispatches'
    id:Mapped[int]=mapped_column(primary_key=True)
    batch_id:Mapped[int]=mapped_column(ForeignKey('dye_batches.id'),unique=True)
    tracking:Mapped[str]=mapped_column(String(80),unique=True)
    customer:Mapped[str]=mapped_column(String(100))
    snapshot:Mapped[dict]=mapped_column(JSON)
    state:Mapped[str]=mapped_column(String(24),default='sent')
    received_by:Mapped[str]=mapped_column(String(100),default='')
    received_at:Mapped[datetime|None]=mapped_column(DateTime,nullable=True)
    conclusion_note:Mapped[str]=mapped_column(String(400),default='')
    sent_by:Mapped[str]=mapped_column(String(120))
class ShadeComplaint(Base):
    __tablename__='shade_complaints'
    __table_args__=(CheckConstraint('requested_kg>0'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    dispatch_id:Mapped[int]=mapped_column(ForeignKey('color_dispatches.id'),unique=True)
    reason:Mapped[str]=mapped_column(String(400))
    requested_kg:Mapped[float]=mapped_column(Float)
    state:Mapped[str]=mapped_column(String(24),default='open')
    decision_note:Mapped[str]=mapped_column(String(400),default='')
    decided_by:Mapped[str]=mapped_column(String(120),default='')
    remake_batch_id:Mapped[int|None]=mapped_column(ForeignKey('dye_batches.id'),unique=True,nullable=True)
    closed_by:Mapped[str]=mapped_column(String(120),default='')
