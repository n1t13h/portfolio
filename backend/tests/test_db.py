from sqlalchemy import text

from app.core.config import Settings
from app.main import create_app


def test_app_exposes_a_working_session_factory(settings: Settings) -> None:
    app = create_app(settings)
    with app.state.session_factory() as session:
        assert session.execute(text("select 1")).scalar() == 1
