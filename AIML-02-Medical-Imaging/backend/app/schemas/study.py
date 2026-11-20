from pydantic import BaseModel, ConfigDict, Field
from typing import Literal


class StudySummary(BaseModel):
 study_id:str
 modality:Literal['XRAY','CT','MRI','UNKNOWN']='UNKNOWN'
 status:str='uploaded'
 created_at:str|None=None
 original_filename: str
 content_type: str
 size_bytes: int = Field(ge=0)

 model_config = ConfigDict(from_attributes=True)
