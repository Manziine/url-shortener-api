import random
import string
import hashlib
from typing import Optional

# Base62 character set (URL-safe, human-readable)
BASE62 = string.ascii_letters + string.digits  # a-z A-Z 0-9


def generate_short_code(length: int = 6) -> str:
    """Generate a random Base62 short code."""
    return "".join(random.choices(BASE62, k=length))


def url_to_code(url: str, length: int = 6) -> str:
    """Deterministically generate a short code from a URL using MD5."""
    hash_bytes = hashlib.md5(url.encode()).digest()
    
    # Convert bytes to integer, then encode to Base62
    num = int.from_bytes(hash_bytes[:8], byteorder="big")
    code = []
    while num > 0 and len(code) < length:
        code.append(BASE62[num % 62])
        num //= 62
    
    return "".join(reversed(code)).ljust(length, "a")


def is_valid_url(url: str) -> bool:
    """Basic URL validation."""
    return url.startswith(("http://", "https://")) and len(url) <= 2048


def is_safe_slug(slug: str) -> bool:
    """Validate custom slug: alphanumeric, hyphens, underscores only."""
    import re
    return bool(re.match(r"^[a-zA-Z0-9_-]{3,50}$", slug))
