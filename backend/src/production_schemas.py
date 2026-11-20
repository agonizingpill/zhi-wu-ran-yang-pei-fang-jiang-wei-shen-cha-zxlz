from pydantic import BaseModel,Field,field_validator,ConfigDict
class RevisionInput(BaseModel):
    model_config=ConfigDict(allow_inf_nan=False)
    parent_recipe_id:int=Field(gt=0)
    child_code:str=Field(min_length=1,max_length=40)
    child_name:str=Field(min_length=1,max_length=100)
    reason:str=Field(min_length=5,max_length=300)
    @field_validator('child_code','child_name','reason')
    @classmethod
    def meaningful(cls,v):
        if not v.strip():raise ValueError('内容不可为空白')
        return v.strip()
class BatchInput(BaseModel):
    code:str=Field(min_length=1,max_length=50)
    approved_trial_id:int=Field(gt=0)
    kg:float=Field(gt=0,le=10000,allow_inf_nan=False)
class BatchMeasurement(BaseModel):
    lab_l:float=Field(ge=0,le=100,allow_inf_nan=False)
    lab_a:float=Field(ge=-128,le=128,allow_inf_nan=False)
    lab_b:float=Field(ge=-128,le=128,allow_inf_nan=False)
