import re

_SEPARATORS = re.compile(r"[_\-\s.]+")
_NUMERIC = re.compile(
    r"^(U?(TINY|SMALL|BIG|HUGE)?INT(EGER)?|FLOAT|DOUBLE|REAL|DECIMAL(\(.*\))?)$"
)


def name_tokens(name: str) -> list[str]:
    """Lowercased words of a column name: split on _ - space . and camelCase boundaries
    (userId -> user, id; APIKey -> api, key; DOB -> dob)."""
    tokens = []
    for part in _SEPARATORS.split(name):
        word = ""
        for i, ch in enumerate(part):
            if word and ch.isupper():
                prev = part[i - 1]
                nxt = part[i + 1] if i + 1 < len(part) else ""
                if not prev.isupper() or nxt.islower():
                    tokens.append(word.lower())
                    word = ""
            word += ch
        if word:
            tokens.append(word.lower())
    return tokens


def last_word(name: str, ignore: frozenset[str] = frozenset()) -> str | None:
    """Last word of a column name, skipping trailing filler words such as "no" or "address"."""
    tokens = [w for w in (re.sub(r"\W", "", t) for t in name_tokens(name)) if w]
    while tokens and tokens[-1] in ignore:
        tokens.pop()
    return tokens[-1] if tokens else None


def is_temporal_type(col_type: str) -> bool:
    """DATE or any TIMESTAMP type (TIMESTAMP_NS, TIMESTAMP WITH TIME ZONE, ...)."""
    t = col_type.upper()
    return t == "DATE" or t.startswith("TIMESTAMP")


def is_numeric_type(col_type: str) -> bool:
    return bool(_NUMERIC.match(col_type.upper()))
