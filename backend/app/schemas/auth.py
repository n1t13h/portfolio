"""Admin login models."""

from pydantic import BaseModel, Field


class LoginBody(BaseModel):
    username: str = Field(max_length=64)
    password: str = Field(max_length=256)
    code: str = Field(max_length=64)  # 6-digit TOTP or a recovery code
