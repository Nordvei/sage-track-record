# Sample signed OVL receipt — external proof artifact

`sample_signed_receipt.json` is **one** OVL attestation receipt produced through SAGE's live
issuer-signing path on 2026-06-19. It is a **demonstration** artifact — its claim is the SPEC
worked-example demo claim (`producer_id: x402-test-agent`, `output_id: demo-forecast-001`), not a
governed closure of any real action. It exists so a third party can run the published verifiers
against a concrete, signed receipt and see what a green check looks like.

## What it lets you check, with no SAGE install

Run both commands from the `published/ovl-verifier/` directory — `ovl_verifier.py`, `verify_signature.py`,
`issuer_keys.json`, and `sample_signed_receipt.json` are all co-located there, so they work by copy-paste.

**1. Keyless re-derivation (the primary proof — no key needed):**
```bash
python3 ovl_verifier.py sample_signed_receipt.json
# -> {"re_derives": true,
#     "recomputed_content_hash": "47c3b4248d820d7556ac64787a20d907b324f9bb5b31bc7e28831b50d2dc9647",
#     "verdict": {"consumed":"READ","realized":"EFFECT","valued":"PASS","independence":"WEAK"}}
```

**2. Issuer signature (the optional, additive signed leg — needs the `cryptography` package):**
```bash
python3 verify_signature.py sample_signed_receipt.json
# -> issuer signature VALID — origin attributable to the issuer key
#    (not non-repudiation / authorization / correctness)
```

## Cross-checks that make this a strong sample

- The `content_hash` `47c3b424…9647` is **identical** to (a) the `SPEC.md` worked example and
  (b) golden vector `pass_capped` in `golden_vectors.json`. The same canonical hash is reproduced
  three independent ways — the documented spec, the pinned vector, and this live receipt.
- The verdict is `PASS / WEAK`: the value-def `beats_baseline` declares `STRONG` independence, but
  because `anchor_obtained` is `false` (caller-submitted evidence) the **honesty cap** lowers it to
  `WEAK`, and `independence_note` says so on the receipt. The receipt is honest about what was *not*
  independently anchored.
- The signature is **strictly additive**: removing the `signature` block leaves the `content_hash`
  byte-identical and `ovl_verifier.py` still re-derives it. The keyless proof never depends on the
  signature.
- The signed leg is **tamper-evident**: altering any envelope field (e.g. `issued_at`) or the
  receipt's `content_hash` makes `verify_signature.py` return INVALID. The signature binds
  `{content_hash, schema, issued_at, ovl_ledger}` plus `issuer_key_id` — not `content_hash` alone —
  so a captured signature cannot be replayed onto a different time or ledger row.

## What a valid signature proves — and what it does not

The issuer signature verifies against the published Ed25519 issuer public key
(`issuer_pubkey.pem` / `issuer_keys.json`, kid `933cf14c4662cc7e`). It proves **origin /
attributability**: this receipt was signed by the holder of that published issuer key.

It does **not** prove, and this artifact does **not** claim:

- non-repudiation
- legal admissibility
- that the attested action was authorized or mandate-bound
- decision correctness
- tamper-proofing or immutability

Those are separate legs and are **not** implemented. For caller-submitted evidence the verdict's
`independence` is `WEAK`, and the receipt verifies *consistency under a versioned value definition*,
not that the world matches the claim.

## The claim stack this artifact demonstrates

1. **Keyless recompute** — `content_hash` is independently recomputable from public inputs
   (`ovl_verifier.py`, stdlib only).
2. **Tamper-evidence** — a modified receipt is detected by recomputation / signature check.
3. **Issuer-signing** — signed receipts verify against the published Ed25519 issuer public key
   (origin/attributability).
4. **Not shipped** — mandate-binding, authority proof, non-repudiation, legal admissibility.

## Provenance

Patent NO 20251414 — BAYGERYCH IFP NORGE. Licensed under this repository's MIT LICENSE.
Part of the SAGE public track record: https://github.com/Nordvei/sage-track-record
