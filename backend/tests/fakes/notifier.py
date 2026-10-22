"""In-memory stand-ins: FakeNotifier."""


class FakeNotifier:
    """Records messages; set `fail` to simulate Telegram being down."""

    def __init__(self) -> None:
        self.sent: list[str] = []
        self.fail = False

    def send(self, text: str) -> None:
        if self.fail:
            raise RuntimeError("telegram is down")
        self.sent.append(text)
