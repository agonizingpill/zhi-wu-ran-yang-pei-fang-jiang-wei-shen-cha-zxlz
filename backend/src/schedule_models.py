from sqlalchemy import String,Float,Boolean,ForeignKey,JSON,CheckConstraint,DateTime,func
from sqlalchemy.orm import Mapped,mapped_column
from .database import Base
class DyeMachine(Base):
    __tablename__='dye_machines'
    id:Mapped[int]=mapped_column(primary_key=True)
    code:Mapped[str]=mapped_column(String(20),unique=True)
    name:Mapped[str]=mapped_column(String(60))
class ScheduleSlot(Base):
    __tablename__='schedule_slots'
    __table_args__=(CheckConstraint('kg>0'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    machine_id:Mapped[int]=mapped_column(ForeignKey('dye_machines.id'))
    code:Mapped[str]=mapped_column(String(50),unique=True)
    recipe_id:Mapped[int]=mapped_column(ForeignKey('dye_recipes.id'))
    recipe_snapshot:Mapped[dict]=mapped_column(JSON)
    kg:Mapped[float]=mapped_column(Float)
    seq:Mapped[int]=mapped_column()
    state:Mapped[str]=mapped_column(String(20),default='planned')
    judgment:Mapped[dict|None]=mapped_column(JSON,nullable=True)
    inspection_reserved:Mapped[bool]=mapped_column(Boolean,default=False)
    start_key:Mapped[str]=mapped_column(String(80),default='')
    started_at:Mapped[object|None]=mapped_column(DateTime,nullable=True)
    completed_at:Mapped[object|None]=mapped_column(DateTime,nullable=True)
    created_by:Mapped[str]=mapped_column(String(120))
    created_at:Mapped[object]=mapped_column(DateTime,server_default=func.now())
class ColorChangeRecord(Base):
    __tablename__='color_change_records'
    id:Mapped[int]=mapped_column(primary_key=True)
    machine_id:Mapped[int]=mapped_column(ForeignKey('dye_machines.id'))
    prev_snapshot:Mapped[dict]=mapped_column(JSON)
    next_snapshot:Mapped[dict]=mapped_column(JSON)
    washed:Mapped[bool]=mapped_column(Boolean,default=False)
    first_delta_e:Mapped[float]=mapped_column(Float)
    source:Mapped[str]=mapped_column(String(20),default='manual')
    slot_id:Mapped[int|None]=mapped_column(ForeignKey('schedule_slots.id'),nullable=True)
    note:Mapped[str]=mapped_column(String(240),default='')
    recorded_by:Mapped[str]=mapped_column(String(120))
    created_at:Mapped[object]=mapped_column(DateTime,server_default=func.now())
class CleaningVoucher(Base):
    __tablename__='cleaning_vouchers'
    id:Mapped[int]=mapped_column(primary_key=True)
    machine_id:Mapped[int]=mapped_column(ForeignKey('dye_machines.id'))
    prev_slot_id:Mapped[int]=mapped_column(ForeignKey('schedule_slots.id'))
    next_slot_id:Mapped[int]=mapped_column(ForeignKey('schedule_slots.id'))
    prev_code:Mapped[str]=mapped_column(String(50))
    next_code:Mapped[str]=mapped_column(String(50))
    state:Mapped[str]=mapped_column(String(20),default='active')
    confirmed_by:Mapped[str]=mapped_column(String(120))
    confirmed_at:Mapped[object]=mapped_column(DateTime,server_default=func.now())
    used_key:Mapped[str]=mapped_column(String(80),default='')
    used_at:Mapped[object|None]=mapped_column(DateTime,nullable=True)
    void_reason:Mapped[str]=mapped_column(String(200),default='')
class ScheduleEvent(Base):
    __tablename__='schedule_events'
    id:Mapped[int]=mapped_column(primary_key=True)
    slot_id:Mapped[int|None]=mapped_column(ForeignKey('schedule_slots.id'),nullable=True)
    kind:Mapped[str]=mapped_column(String(20))
    actor:Mapped[str]=mapped_column(String(120))
    detail:Mapped[dict]=mapped_column(JSON)
    at:Mapped[object]=mapped_column(DateTime,server_default=func.now())
