from datetime import date
from typing import Literal
from pydantic import BaseModel,Field,ConfigDict,field_validator
class Inputs(BaseModel):
    model_config=ConfigDict(allow_inf_nan=False)
    @field_validator('*',mode='before')
    @classmethod
    def trim(cls,v):
        if isinstance(v,str):return v.strip()
        return v
class LotInput(Inputs):
    code:str=Field(min_length=1,max_length=50)
    component:Literal['A','B','C']
    available_kg:float=Field(gt=0,le=10000)
    expires_on:date
class LotStateInput(Inputs):
    state:Literal['active','quarantine']
class IssueInput(Inputs):
    batch_id:int=Field(gt=0)
    lot_a_id:int=Field(gt=0)
    lot_b_id:int=Field(gt=0)
    lot_c_id:int=Field(gt=0)
class DispatchInput(Inputs):
    batch_id:int=Field(gt=0)
    tracking:str=Field(min_length=3,max_length=80)
    customer:str=Field(min_length=2,max_length=100)
class ReceiptInput(Inputs):
    received_by:str=Field(min_length=2,max_length=100)
class ConclusionInput(Inputs):
    batch_id:int=Field(gt=0)
    conclusion:Literal['accepted','disputed']
    note:str=Field(min_length=5,max_length=400)
class ComplaintInput(Inputs):
    dispatch_id:int=Field(gt=0)
    reason:str=Field(min_length=5,max_length=400)
    requested_kg:float=Field(gt=0,le=10000)
class DecisionInput(Inputs):
    decision:Literal['remake_approved','rejected']
    note:str=Field(min_length=5,max_length=400)
class RemakeInput(Inputs):
    code:str=Field(min_length=1,max_length=50)
    approved_trial_id:int=Field(gt=0)
class ComplaintCloseInput(Inputs):
    batch_id:int=Field(gt=0)
