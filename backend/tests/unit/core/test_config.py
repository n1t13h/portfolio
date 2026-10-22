import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.mark.parametrize("prefix", ["short", "has/slash/in/it/xxxxxx", "has space in it xxxxxx"])
def test_admin_prefix_must_be_long_and_url_safe(prefix: str) -> None:
    with pytest.raises(ValidationError):
        Settings(admin_path_prefix=prefix, session_secret="s" * 16, cdn_base_url="https://c")
