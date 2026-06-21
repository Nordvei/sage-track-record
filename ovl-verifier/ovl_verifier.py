"""Standalone OVL attestation verifier — spec ovl.attestation.v1.

Re-derive any OVL receipt's verdict and content_hash from public inputs, with ZERO SAGE
dependencies (Python standard library only: json + hashlib). "Trust the math, not the issuer":
recompute evaluate(claim, value_def) + the honesty cap, hash {claim, verdict, value_def,
anchor_obtained}, and check it equals the receipt's content_hash.

This is intended to be the SINGLE SOURCE OF TRUTH for the OVL content-hash — the SAME code the
issuer runs on-box AND the code published for external agents — so a published verifier can never
drift from what the server actually computes. A conformance test (tests/test_ovl_verifier.py)
asserts this module's output equals the live o2_gateway.attestation.attest across golden vectors.

Canonical form (must match byte-for-byte to reproduce a hash):
  sha256( json.dumps({"claim","verdict","value_def","anchor_obtained"},
                     sort_keys=True, separators=(",", ":")).encode("utf-8") ).hexdigest()
Cross-language note: the main reproduction risk is JSON number formatting (e.g. 0.1+0.2) and key
order. This Python module is the reference; non-Python ports should follow RFC 8785 (JCS) and the
published golden vectors. content_hash deliberately covers ONLY claim+verdict+value_def+
anchor_obtained — never timestamp, issuer, detail, or ledger seq — so it is deterministic and
time-independent (the same claim always yields the same hash).

Patent: NO 20251414 — BAYGERYCH IFP NORGE.
"""
from __future__ import annotations
import json
import hashlib

# ── verdict vocabulary as plain strings (no dependency on ovl.model) ─────────
CONSUMED_READ, CONSUMED_UNREAD = "READ", "UNREAD"
REALIZED_EFFECT, REALIZED_NO_OP = "EFFECT", "NO_OP"
_REALIZED = {"EFFECT", "NO_OP", "FAILED", "RETRY_DISCARDED"}
VALUED_PASS, VALUED_FAIL, VALUED_INDETERMINATE, VALUED_SKIPPED = "PASS", "FAIL", "INDETERMINATE", "SKIPPED"
INDEP_STRONG, INDEP_WEAK, INDEP_NONE = "STRONG", "WEAK", "NONE"

# ── Layer-3 value definitions (mirror ovl/value_defs.py; versioned) ──────────
# Independence is a property of the ground-truth SOURCE: external/adversarial = STRONG;
# producer-owned = WEAK. Declared here, disclosed on every verdict, and capped below.
_BEATS_MARGIN = 0.02          # BeatsBestBaseline.MARGIN
_BEATS_MIN_N = 30             # BeatsBestBaseline.MIN_N
_BEATS_BASELINE_VERSION = "deoverlap_vs_max(persistence,anti_persistence)_2026-06-05"


def _score_beats_baseline(meta: dict) -> str:
    """beats_baseline: realized directional accuracy must beat the STRONGEST simple baseline by a
    margin and clear chance. Ground truth = external market settlement -> STRONG independence."""
    acc = meta.get("accuracy")
    per = meta.get("persistence")
    anti = meta.get("anti_persistence")
    n = int(meta.get("n", 0) or 0)
    if acc is None or per is None or anti is None or n < _BEATS_MIN_N:
        return VALUED_INDETERMINATE
    best = max(per, anti)
    if acc > best + _BEATS_MARGIN and acc > 0.52:
        return VALUED_PASS
    return VALUED_FAIL


def _value_def(name: str):
    """Return (independence, score_fn) for a value-def name. Only 'beats_baseline' is STRONG; every
    other name resolves to consumption_only (WEAK, always INDETERMINATE — no external anchor)."""
    if name == "beats_baseline":
        return INDEP_STRONG, _score_beats_baseline
    return INDEP_WEAK, (lambda meta: VALUED_INDETERMINATE)


def _coerce_realized(sig) -> str:
    if sig is None:
        return REALIZED_NO_OP
    return sig if sig in _REALIZED else REALIZED_NO_OP


def evaluate(claim: dict, value_def: str, anchor_obtained: bool) -> dict:
    """Reproduce the 3-layer fail-early engine (consumed -> realized -> valued) + honesty cap.
    Returns the verdict dict {consumed, realized, valued, independence}.

    A later layer never rescues an earlier failure: an unread output never reaches the value test.
    """
    # Layer 1 — consumed?
    if not claim.get("consumed_signal"):
        return {"consumed": CONSUMED_UNREAD, "realized": REALIZED_NO_OP,
                "valued": VALUED_SKIPPED, "independence": INDEP_NONE}
    # Layer 2 — realized?
    realized = _coerce_realized(claim.get("realized_signal"))
    if realized != REALIZED_EFFECT:
        return {"consumed": CONSUMED_READ, "realized": realized,
                "valued": VALUED_SKIPPED, "independence": INDEP_NONE}
    # Layer 3 — valued? (pluggable, externally/adversarially anchored)
    independence, score_fn = _value_def(value_def)
    valued = score_fn(claim.get("meta") or {})
    # Honesty cap — caller-submitted evidence (no SAGE-performed anchor) can never be STRONG.
    if not anchor_obtained and independence == INDEP_STRONG:
        independence = INDEP_WEAK
    return {"consumed": CONSUMED_READ, "realized": REALIZED_EFFECT,
            "valued": valued, "independence": independence}


def content_hash(claim: dict, verdict: dict, value_def: str, anchor_obtained: bool) -> str:
    """The canonical, deterministic content hash. Reproducible from public inputs alone."""
    core = {"claim": claim, "verdict": verdict, "value_def": value_def,
            "anchor_obtained": bool(anchor_obtained)}
    return hashlib.sha256(
        json.dumps(core, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def verify(receipt: dict):
    """Independently re-derive an OVL receipt. Returns (ok: bool, recomputed_hash: str).

    receipt requires: claim (dict), value_def (str), anchor_obtained (bool), content_hash (str).
    ok is True iff the recomputed hash equals receipt['content_hash'] — i.e. the issuer's verdict
    is reproducible from the public inputs and this published algorithm.
    """
    claim = receipt["claim"]
    value_def = receipt.get("value_def", "consumption")
    anchor = bool(receipt.get("anchor_obtained", False))
    verdict = evaluate(claim, value_def, anchor)
    recomputed = content_hash(claim, verdict, value_def, anchor)
    return (recomputed == receipt.get("content_hash")), recomputed


if __name__ == "__main__":
    import sys
    rec = json.load(open(sys.argv[1])) if len(sys.argv) > 1 else json.load(sys.stdin)
    ok, h = verify(rec)
    print(json.dumps({"re_derives": ok, "recomputed_content_hash": h,
                      "verdict": evaluate(rec["claim"], rec.get("value_def", "consumption"),
                                          bool(rec.get("anchor_obtained", False)))}, indent=2))
    sys.exit(0 if ok else 1)
