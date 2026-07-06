from pydantic import BaseModel, Field

class LoginRequest(BaseModel):
    username: str = Field(..., description="The username of the user")
    password: str = Field(..., description="The password of the user")