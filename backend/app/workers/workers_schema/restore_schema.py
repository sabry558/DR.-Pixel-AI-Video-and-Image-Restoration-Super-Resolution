from pydantic import BaseModel
class RestoreSchema(BaseModel):
    job_id:int
    start_frame:int
    end_frame:int
