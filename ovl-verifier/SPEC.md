# OVL Attestation Verification — `ovl.attestation.v1`

This spec lets **anyone** independently re-derive a SAGE OVL attestation from its public inputs and
check the `content_hash` — *trust the math, not the issuer*. `ovl_verifier.py` in this directory is
the reference implementation (Python stdlib only) and is the **same code the issuer runs** to produce
the hash, so a receipt that fails this check could not have been issued.

## What an attestation is
SAGE evaluates an agent's submitted work-claim through a 3-layer, fail-early engine and returns a
re-derivable receipt. The verdict is `consumed → realized → valued`, plus an `independence` axis
describing how strong the ground-truth anchor is.

A receipt contains (among envelope fields) the four things the hash is computed over:
```json
{ "claim": { ... }, "value_def": "beats_baseline", "anchor_obtained": false,
  "verdict": {"consumed":"READ","realized":"EFFECT","valued":"PASS","independence":"WEAK"},
  "content_hash": "47c3b424...9647" }
```

## Verification algorithm
Given `claim`, `value_def`, `anchor_obtained`:

1. **Layer 1 — consumed?** `READ` if `claim.consumed_signal` is truthy, else `UNREAD`. If `UNREAD` →
   verdict `{UNREAD, NO_OP, SKIPPED, NONE}` (stop).
2. **Layer 2 — realized?** coerce `claim.realized_signal` to one of
   `EFFECT|NO_OP|FAILED|RETRY_DISCARDED` (anything else / null → `NO_OP`). If not `EFFECT` →
   verdict `{READ, <realized>, SKIPPED, NONE}` (stop).
3. **Layer 3 — valued?** by `value_def` (below); independence is the value-def's declared source
   strength.
4. **Honesty cap.** If `anchor_obtained` is false and independence is `STRONG`, lower it to `WEAK`.
   (Caller-submitted evidence can never claim STRONG; only a SAGE-performed anchor fetch can.)
5. **content_hash** = `sha256(canonical_json({claim, verdict, value_def, anchor_obtained}))`.

`content_hash` covers **only** those four fields — never timestamp, issuer, detail, or ledger
sequence — so it is deterministic and time-independent (the same claim always yields the same hash).

## Value definitions (versioned)
- **`beats_baseline`** — independence **STRONG** (external market settlement). Reads
  `claim.meta {accuracy, persistence, anti_persistence, n}`. If any of accuracy/persistence/
  anti_persistence is missing or `n < 30` → `INDETERMINATE`. Else `best = max(persistence,
  anti_persistence)`; `PASS` iff `accuracy > best + 0.02` **and** `accuracy > 0.52`; else `FAIL`.
  baseline_version: `deoverlap_vs_max(persistence,anti_persistence)_2026-06-05`.
- **anything else (`consumption`)** — independence **WEAK**, always `INDETERMINATE` (no external
  value anchor).

## Canonical JSON (must match byte-for-byte)
```
sha256( json.dumps(core, sort_keys=True, separators=(",", ":")).encode("utf-8") ).hexdigest()
```
where `core = {"claim": <claim>, "verdict": <verdict>, "value_def": <str>, "anchor_obtained": <bool>}`.
- Keys sorted (recursively), no whitespace, UTF-8.
- **Cross-language note:** the only real reproduction risk is JSON number formatting (e.g.
  `0.1+0.2`) and key order. The Python reference is authoritative; non-Python ports should follow
  **RFC 8785 (JSON Canonicalization Scheme)** and validate against `golden_vectors.json`.

## Worked example
The demo claim
`{"producer_id":"x402-test-agent","output_id":"demo-forecast-001","operation":"forecast",
"consumed_signal":true,"realized_signal":"EFFECT","value_def":"beats_baseline",
"meta":{"accuracy":0.80,"persistence":0.40,"anti_persistence":0.60,"n":200}}` with
`anchor_obtained=false` →
`best=0.60`, `0.80 > 0.62` → `PASS`; independence `STRONG` capped to `WEAK`; →
`content_hash = 47c3b4248d820d7556ac64787a20d907b324f9bb5b31bc7e28831b50d2dc9647`.
(See `golden_vectors.json` for PASS/FAIL/INDETERMINATE/SKIPPED + cap on/off.)

## What this proves — and does not
- **Proves:** the verdict is reproducible from public inputs + this published algorithm; the issuer
  cannot assert a verdict the math doesn't support.
- **Does not prove ground truth.** For caller-submitted evidence independence is `WEAK` — the
  receipt verifies *consistency under a versioned value definition*, not that the world matches the
  claim. A `WEAK` verdict is honest about exactly that.
- **Mandate is REFERENCED, not authorized.** A receipt MAY bind a `mandate` object
  `{sub, scope, jti, exp, budget, service_tier, mandate_hash, status}` into the signed envelope (it
  rides the signature, never `content_hash` → keyless re-derivation + golden vectors are unchanged).
  `status` is `REFERENCED_UNVERIFIED` (the mandate the OAuth-AS / payment rail already verified, bound
  here by reference) or `UN-MANDATED` (no authenticated mandate — marked, never fabricated). A valid
  signature proves the issuer BOUND this mandate reference to this verdict; it does **not** prove the
  mandate was authorized, valid, or sufficient — that remains the auth/payment rail's attestation.

## How the mandate is bound (signed-envelope coverage, not `content_hash`)
Mandate binding is by the **Ed25519 signature over the receipt envelope**, NOT by the keyless
`content_hash`. The two legs are independent, and both must be understood to confirm a mandate is
cryptographically bound rather than merely displayed:

- **`content_hash` is unchanged and excludes the mandate.** It covers only `{claim, verdict,
  value_def, anchor_obtained}` — so keyless re-derivation and the golden vectors are byte-identical
  whether or not a mandate is present.
- **The signed envelope includes the mandate.** The Ed25519 signature is computed over the canonical
  envelope `{content_hash, schema, issued_at, ovl_ledger, mandate, issuer_key_id}` (the issuer signer
  injects `issuer_key_id` before signing), so the `bound_mandate` reference is part of the signed
  bytes. Read it with `bound_mandate(receipt)`.
- **Same `content_hash` + different mandate must produce a different signature.** Because the mandate
  is in the signed bytes, two receipts with an identical `content_hash` but different mandates have
  different signatures. If the signature only covered `content_hash`, they would be identical — that
  is the test that distinguishes *bound* from *merely displayed*.
- **A grafted or escalated mandate under an existing signature must fail verification.** Splicing a
  different/escalated mandate into a receipt while keeping its signature — or altering the top-level
  `mandate` convenience copy — makes `verify_signature(receipt)` return `False` (the top-level copy is
  cross-checked against the signed one).

**Boundary.** This proves only that the mandate reference is **bound into the signed receipt
envelope** — that the issuer signed a receipt carrying this mandate. It does **not** prove
correctness, legal validity, user consent, non-repudiation, or legal admissibility; nor that the
mandate itself was authorized, valid, or sufficient.

## Provenance
Patent NO 20251414 — BAYGERYCH IFP NORGE. Licensed under this repository's MIT LICENSE.
