"""Admin login models."""

from pydantic import BaseModel, ConfigDict, Field


class LoginBody(BaseModel):
    username: str = Field(max_length=64)
    password: str = Field(max_length=256)
    code: str = Field(max_length=64)  # 6-digit TOTP or a recovery code


class AdminOut(BaseModel):
    """The signed-in admin, as far as the API needs to know."""

    model_config = ConfigDict(from_attributes=True)

    username: str
