from __future__ import annotations

from hashlib import sha256
import json
import re
import unicodedata
from typing import Any


_SEPARATOR_RE = re.compile(r"[\s\-_./\\:;|,，。；：、（）()【】\[\]{}<>《》\"'`~!！?？]+")


def normalize_identity_text(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold().strip()
    text = _SEPARATOR_RE.sub(" ", text)
    return " ".join(text.split())


def short_identity_hash(payload: Any, *, length: int = 12) -> str:
    normalized = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return sha256(normalized.encode("utf-8")).hexdigest()[:length]
