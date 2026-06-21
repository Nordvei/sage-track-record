# OVL Attestation Verifier

**Re-derive any SAGE OVL attestation yourself — trust the math, not the issuer.**

SAGE issues re-derivable receipts ("attestations") that evaluate an agent's work-claim. This
directory lets any third party independently recompute a receipt's verdict and `content_hash` from
its public inputs, with **zero SAGE dependencies** — Python standard library only.

`ovl_verifier.py` here is the **same code the issuer runs** to compute the hash (single source of
truth, not a re-implementation). A runtime guard on the issuer side refuses to emit any receipt that
this verifier could not reproduce, and a CI conformance test pins the two together — so a green
check here means the receipt matches what SAGE actually computed.

## Quick start
Verify a receipt you were given (any machine, no SAGE install):
```bash
python3 ovl_verifier.py receipt.json
# -> {"re_derives": true, "recomputed_content_hash": "47c3b424…", "verdict": {...}}
```
Confirm this verifier reproduces the published reference vectors:
```bash
python3 selftest.py
# -> 7 vectors, 7 reproduced, 0 failures
```
As a library:
```python
import ovl_verifier
ok, recomputed_hash = ovl_verifier.verify(receipt)   # ok == (recomputed_hash == receipt["content_hash"])
```

## Files
- `ovl_verifier.py` — the keyless verifier (stdlib only: `json`, `hashlib`).
- `verify_signature.py` — the OPTIONAL issuer-signature leg (needs `cryptography`): verifies the
  Ed25519 `signature` over the signed envelope, proving ORIGIN (issuer-key holder) — not
  authorization/correctness. Also exposes `bound_mandate(receipt)`.
- `issuer_keys.json` / `issuer_pubkey.pem` — the published issuer verification key(s) (kid + PEM). Also
  served live at `/.well-known/ovl-issuer-keys.json` and `/.well-known/ovl-issuer.pem`.
- `golden_vectors.json` — reference receipts (PASS / FAIL / INDETERMINATE / SKIPPED, honesty cap on+off).
- `selftest.py` — reproduces every vector; exit 0 = match.
- `SPEC.md` — the `ovl.attestation.v1` verification algorithm, canonical-JSON rules, and value-def formulas.
- `PAYMENT_EVIDENCE.md` — how to correlate a paid receipt to its x402 settlement (the door emits no
  `X-PAYMENT-RESPONSE`; the reference is the on-chain tx ↔ `x402_payments`/`o2_transactions`).

## What a verified receipt means
`content_hash` covers exactly `{claim, verdict, value_def, anchor_obtained}` — nothing about who
issued it or when. A match proves the verdict is reproducible from public inputs and the published
algorithm. It proves **consistency**, not ground truth: for caller-submitted evidence the
`independence` is `WEAK`, and the receipt is honest about that (see `SPEC.md`).

## Provenance & license
Patent NO 20251414 — BAYGERYCH IFP NORGE. Code under this repository's MIT LICENSE.
Part of the SAGE public track record: https://github.com/Nordvei/sage-track-record
