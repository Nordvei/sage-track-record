#!/usr/bin/env python3
"""OVL issuer-signature verifier — the OPTIONAL signed leg.

The PRIMARY proof of an OVL receipt is KEYLESS: recompute content_hash with ovl_verifier.py (stdlib
only, no key — a forged signature cannot survive that recomputation). This module verifies the
OPTIONAL additive issuer SIGNATURE: it confirms a receipt was signed by the holder of the published
issuer key — i.e. ORIGIN / integrity attributable to that key.

It does NOT establish anything stronger. An issuer signature is NOT non-repudiation, NOT legal
admissibility, NOT a proof of correctness, and NOT tamper-proofing. A receipt MAY also bind a
mandate REFERENCE (status REFERENCED_UNVERIFIED, or UN-MANDATED when absent) into the signed
envelope: a valid signature proves the issuer BOUND that mandate reference to this verdict — NOT
that the mandate was authorized, valid, or sufficient (the OAuth-AS / payment rail own that). Read
it with bound_mandate(). Those stronger legs are not implemented here.

Unlike ovl_verifier.py (stdlib only), this verifier needs the `cryptography` package.

    python3 verify_signature.py receipt.json
    from verify_signature import verify_signature; verify_signature(receipt) -> True | False | None

Patent: NO 20251414 — BAYGERYCH IFP NORGE.
"""
from __future__ import annotations
import json
import base64
import sys
from pathlib import Path

_KEYS_PATH = Path(__file__).with_name("issuer_keys.json")


def _load_keys() -> dict:
    try:
        data = json.loads(_KEYS_PATH.read_text())
        return {k["kid"]: k["pubkey_pem"] for k in data.get("keys", [])}
    except Exception:
        return {}


def verify_signature(receipt: dict):
    """Return True if the receipt's issuer signature is valid, False if present-but-invalid, or None
    if the receipt carries no signature (a keyless receipt — verify it via ovl_verifier.content_hash
    instead). Never raises."""
    block = receipt.get("signature")
    if not block:
        return None
    try:
        from cryptography.hazmat.primitives.serialization import load_pem_public_key
        pubkey_pem = _load_keys().get(block["kid"])
        if not pubkey_pem:
            return False  # unknown / unpublished key id
        env = block["signed_envelope"]
        # the signature must bind to THIS receipt's content_hash (no attaching a foreign signature)
        if env.get("content_hash") != receipt.get("content_hash"):
            return False
        # likewise the top-level mandate convenience copy must equal the SIGNED one, so a relying
        # party that reads receipt['mandate'] directly can never trust an unsigned, altered copy.
        if "mandate" in receipt and receipt.get("mandate") != env.get("mandate"):
            return False
        msg = json.dumps(env, sort_keys=True, separators=(",", ":")).encode("utf-8")
        load_pem_public_key(pubkey_pem.encode()).verify(base64.b64decode(block["sig"]), msg)
        return True
    except Exception:
        return False


def bound_mandate(receipt: dict):
    """Return the mandate REFERENCE bound into the signed envelope, or None if the receipt is
    unsigned. The mandate is REFERENCED_UNVERIFIED (or UN-MANDATED): a valid signature
    (verify_signature(receipt) is True) proves the issuer BOUND this mandate reference to this
    verdict — it does NOT prove the mandate was authorized, valid, or sufficient. Always confirm
    verify_signature(receipt) is True before relying on the returned value."""
    block = receipt.get("signature")
    if not block:
        return None
    return (block.get("signed_envelope") or {}).get("mandate")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: verify_signature.py <receipt.json>")
        sys.exit(2)
    result = verify_signature(json.loads(Path(sys.argv[1]).read_text()))
    print({
        None: "no issuer signature (keyless receipt — verify content_hash with ovl_verifier.py)",
        True: "issuer signature VALID — origin attributable to the issuer key (not non-repudiation / authorization / correctness)",
        False: "issuer signature INVALID",
    }[result])
    sys.exit(0 if result in (True, None) else 1)
