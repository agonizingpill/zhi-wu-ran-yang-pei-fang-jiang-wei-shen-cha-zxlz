import math
from pydantic import BaseModel,Field,field_validator
class Login(BaseModel):
    email:str
    password:str
class RecipeInput(BaseModel):
    code:str=Field(min_length=1,max_length=40)
    name:str=Field(min_length=1,max_length=100)
    dye_a:float=Field(ge=0,le=100)
    dye_b:float=Field(ge=0,le=100)
    dye_c:float=Field(ge=0,le=100)
class SwatchInput(BaseModel):
    recipe_id:int
    lot:str=Field(min_length=1,max_length=60)
    spectrum:list[float]=Field(min_length=36,max_length=36)
    l:float=Field(ge=0,le=100)
    a:float=Field(ge=-128,le=128)
    b:float=Field(ge=-128,le=128)
    @field_validator('spectrum')
    @classmethod
    def valid_spectrum(cls,v):
        if any(not math.isfinite(x) or x<0 or x>1 for x in v):raise ValueError('36 波段反射率必须在 0–1 之间')
        return v
class TrialInput(BaseModel):
    recipe_id:int
    reference_swatch_id:int
    candidate_swatch_id:int
    note:str=Field(default='',max_length=240)
