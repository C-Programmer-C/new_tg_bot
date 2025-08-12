import base64
import hashlib
import hmac
import logging
from typing import Dict, Optional
from config import settings


logging.basicConfig(level=logging.DEBUG)

def verify_signature(header_sig: Optional[str], body: bytes) -> bool:
    if not settings.WEBHOOK_SECURITY_KEY:
        logging.warning("No PYRUS_BOT_SECRET configured; skipping signature verification.")
        return False
    if not header_sig:
        logging.debug("No signature header provided")
        return False



    expected_sig = hmac.new(settings.WEBHOOK_SECURITY_KEY.encode("utf-8"), body, hashlib.sha1).hexdigest()


    logging.debug(f"Expected signature: {expected_sig}")
    logging.debug(f"Received signature: {header_sig}")

    return hmac.compare_digest(header_sig, expected_sig)