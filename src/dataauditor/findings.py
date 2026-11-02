from dataclasses import dataclass


@dataclass(frozen=True)
class Finding:
    check: str
    severity: str
    column: str | None
    message: str
    count: int
    examples: tuple[str, ...] = ()
