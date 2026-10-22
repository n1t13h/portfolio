"""Dependencies for the public routes."""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.services.public_views import PublicViews


def get_public_views(session: Session = Depends(get_session)) -> PublicViews:
    return PublicViews(session)
