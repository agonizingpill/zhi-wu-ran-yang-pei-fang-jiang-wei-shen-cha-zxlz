from pydantic import BaseModel,Field,field_validator,ConfigDict
class SlotInput(BaseModel):
    model_config=ConfigDict(allow_inf_nan=False)
    machine_id:int=Field(gt=0)
    code:str=Field(min_length=1,max_length=50)
    recipe_id:int=Field(gt=0)
    kg:float=Field(gt=0,le=10000)
    before_slot_id:int|None=Field(default=None,gt=0)
    @field_validator('code')
    @classmethod
    def meaningful(cls,v):
        if not v.strip():raise ValueError('内容不可为空白')
        return v.strip()
class RescheduleInput(BaseModel):
    machine_id:int=Field(gt=0)
    before_slot_id:int|None=Field(default=None,gt=0)
class StartInput(BaseModel):
    request_key:str|None=Field(default=None,max_length=80)
class CompleteInput(BaseModel):
    first_delta_e:float=Field(ge=0,le=100,allow_inf_nan=False)
class HistoryInput(BaseModel):
    model_config=ConfigDict(allow_inf_nan=False)
    machine_id:int=Field(gt=0)
    prev_recipe_id:int=Field(gt=0)
    next_recipe_id:int=Field(gt=0)
    washed:bool=False
    first_delta_e:float=Field(ge=0,le=100)
    note:str=Field(default='',max_length=240)
class WashInput(BaseModel):
    slot_id:int=Field(gt=0)
