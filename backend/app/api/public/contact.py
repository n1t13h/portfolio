"""Public contact form endpoint."""

import re
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel, Field, StringConstraints

from app.services.contact import ContactService, RateLimited

router = APIRouter(tags=["contact"])

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

Text = Annotated[str, StringConstraints(strip_whitespace=True)]


class ContactBody(BaseModel):
    name: Text = Field(min_length=1, max_length=100)
    email: Text = Field(max_length=254, pattern=EMAIL.pattern)
    message: Text = Field(min_length=1, max_length=5000)
    website: str = ""  # honeypot: real visitors never see or fill this


@router.post("/contact", status_code=202)
def contact(body: ContactBody, request: Request, background: BackgroundTasks) -> dict[str, str]:
    if body.website:  # a bot filled the hidden field: pretend success, keep nothing
        return {"status": "received"}
    state = request.app.state
    service = ContactService(state.session_factory, state.notifier, state.settings, state.clock)
    ip = request.client.host if request.client else ""
    try:
        service.submit(body.name, body.email, body.message, ip)
    except RateLimited:
        raise HTTPException(status_code=429, detail="too many messages, try again later") from None
    background.add_task(service.deliver_pending)  # after the response, so Telegram can't slow it
    return {"status": "received"}
