"""Password hashing and Bangladesh mobile-number normalization."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets

from fastapi import HTTPException

_PBKDF2_ROUNDS = 180_000


def normalize_mobile(raw: str) -> str:
    """Store as 01XXXXXXXXX. Accept +8801… / 8801… / 01…."""
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("880") and len(digits) >= 13:
        digits = "0" + digits[3:]
    if len(digits) == 10 and digits.startswith("1"):
        digits = "0" + digits
    if not re.fullmatch(r"01[3-9]\d{8}", digits):
        raise HTTPException(
            status_code=400,
            detail="মোবাইল নম্বর ঠিক নয়। 01XXXXXXXXX আকারে লিখুন।",
        )
    return digits


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("ascii"), _PBKDF2_ROUNDS
    ).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split("$", 1)
    except ValueError:
        return False
    check = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("ascii"), _PBKDF2_ROUNDS
    ).hex()
    return hmac.compare_digest(check, digest)


def new_token() -> str:
    return secrets.token_hex(32)
