import random
from pathlib import Path
from typing import List, Optional


_BUILTIN_UAS: List[str] = [
    # Desktop
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    # Mobile
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
]


def load_ua_list(path: Optional[str]) -> List[str]:
    if not path:
        return list(_BUILTIN_UAS)

    p = Path(path)
    if not p.is_file():
        return list(_BUILTIN_UAS)

    uas: List[str] = []
    with p.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            uas.append(line)

    return uas or list(_BUILTIN_UAS)


def pick_random_ua(uas: List[str], fallback: str) -> str:
    if not uas:
        return fallback
    return random.choice(uas)

