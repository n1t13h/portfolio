from pathlib import Path

from app.core.config import Settings


def test_env_example_documents_every_setting() -> None:
    lines = (Path(__file__).parents[3] / ".env.example").read_text().splitlines()
    documented = {line.split("=")[0].strip().lower() for line in lines if "=" in line}
    assert documented == set(Settings.model_fields)
