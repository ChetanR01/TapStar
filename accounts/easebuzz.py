"""
Easebuzz payment client — direct REST API, no SDK.

Flow:
1. initiate_payment(...) → POST /payment/initiateLink → returns {status, data: access_key}
2. Redirect user to {PAY_BASE}/pay/{access_key}
3. User pays on Easebuzz hosted page
4. Easebuzz POSTs back to our surl (success) or furl (failure) with transaction details + hash
5. verify_callback_hash(...) validates the returned hash

Forward hash (for initiate): sha512(key|txnid|amount|productinfo|firstname|email|udf1..udf10|salt)
Reverse hash (for callback): sha512(salt|status|udf10..udf1|email|firstname|productinfo|amount|txnid|key)
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from urllib.parse import urlencode

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


ENV_TEST = "test"
ENV_PROD = "prod"

API_BASE = {
    ENV_TEST: "https://testpay.easebuzz.in",
    ENV_PROD: "https://pay.easebuzz.in",
}

PAY_BASE = {
    ENV_TEST: "https://testpay.easebuzz.in",
    ENV_PROD: "https://pay.easebuzz.in",
}


@dataclass
class InitiateParams:
    txnid: str
    amount_rupees: str  # "499.00" — Easebuzz expects rupees (decimal string) not paise
    product_info: str
    first_name: str
    email: str
    phone: str
    success_url: str  # surl
    failure_url: str  # furl
    udf1: str = ""
    udf2: str = ""
    udf3: str = ""
    udf4: str = ""
    udf5: str = ""


@dataclass
class InitiateResult:
    success: bool
    access_key: str = ""
    pay_url: str = ""
    error: str = ""
    raw: dict | None = None


def _hash_fields(key: str, salt: str, p: InitiateParams) -> str:
    """
    Easebuzz forward hash:
    sha512(key|txnid|amount|productinfo|firstname|email|udf1|udf2|udf3|udf4|udf5|udf6|udf7|udf8|udf9|udf10|salt)
    """
    parts = [
        key,
        p.txnid,
        p.amount_rupees,
        p.product_info,
        p.first_name,
        p.email,
        p.udf1, p.udf2, p.udf3, p.udf4, p.udf5,
        "", "", "", "", "",  # udf6..udf10
        salt,
    ]
    raw = "|".join(parts)
    return hashlib.sha512(raw.encode("utf-8")).hexdigest()


def initiate_payment(p: InitiateParams) -> InitiateResult:
    key = settings.EASEBUZZ_KEY
    salt = settings.EASEBUZZ_SALT
    env = getattr(settings, "EASEBUZZ_ENV", ENV_TEST)

    if not key or not salt:
        return InitiateResult(success=False, error="Easebuzz not configured (set EASEBUZZ_KEY/EASEBUZZ_SALT).")

    payload = {
        "key": key,
        "txnid": p.txnid,
        "amount": p.amount_rupees,
        "productinfo": p.product_info,
        "firstname": p.first_name,
        "email": p.email,
        "phone": p.phone,
        "surl": p.success_url,
        "furl": p.failure_url,
        "udf1": p.udf1, "udf2": p.udf2, "udf3": p.udf3, "udf4": p.udf4, "udf5": p.udf5,
        "hash": _hash_fields(key, salt, p),
    }

    url = f"{API_BASE[env]}/payment/initiateLink"
    try:
        resp = requests.post(url, data=payload, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.exception("Easebuzz initiate failed: %s", exc)
        return InitiateResult(success=False, error=f"Network error calling Easebuzz: {exc}")

    try:
        body = resp.json()
    except ValueError:
        return InitiateResult(success=False, error=f"Invalid JSON from Easebuzz: {resp.text[:200]}")

    # Easebuzz returns status 1 on success, else error details in data
    if str(body.get("status")) != "1":
        return InitiateResult(success=False, error=str(body.get("data") or body)[:500], raw=body)

    access_key = body.get("data") or ""
    return InitiateResult(
        success=True,
        access_key=access_key,
        pay_url=f"{PAY_BASE[env]}/pay/{access_key}",
        raw=body,
    )


def verify_callback_hash(posted: dict) -> bool:
    """
    Verify the `hash` field Easebuzz posts on success/failure callback.

    Reverse hash:
    sha512(salt|status|udf10|udf9|udf8|udf7|udf6|udf5|udf4|udf3|udf2|udf1|email|firstname|productinfo|amount|txnid|key)
    """
    key = settings.EASEBUZZ_KEY
    salt = settings.EASEBUZZ_SALT
    if not key or not salt:
        return False

    posted_hash = (posted.get("hash") or "").lower().strip()
    if not posted_hash:
        return False

    parts = [
        salt,
        posted.get("status", ""),
        posted.get("udf10", ""), posted.get("udf9", ""), posted.get("udf8", ""),
        posted.get("udf7", ""), posted.get("udf6", ""), posted.get("udf5", ""),
        posted.get("udf4", ""), posted.get("udf3", ""), posted.get("udf2", ""),
        posted.get("udf1", ""),
        posted.get("email", ""),
        posted.get("firstname", ""),
        posted.get("productinfo", ""),
        posted.get("amount", ""),
        posted.get("txnid", ""),
        key,
    ]
    expected = hashlib.sha512("|".join(parts).encode("utf-8")).hexdigest()
    return expected.lower() == posted_hash


def build_pay_url(access_key: str) -> str:
    env = getattr(settings, "EASEBUZZ_ENV", ENV_TEST)
    return f"{PAY_BASE[env]}/pay/{access_key}"
