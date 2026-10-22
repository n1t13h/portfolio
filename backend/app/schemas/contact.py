"""Contact form model."""

import re
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

Text = Annotated[str, StringConstraints(strip_whitespace=True)]


class ContactBody(BaseModel):
    name: Text = Field(min_length=1, max_length=100)
    email: Text = Field(max_length=254, pattern=EMAIL.pattern)
    message: Text = Field(min_length=1, max_length=5000)
    website: str = ""  # honeypot: real visitors never see or fill this
