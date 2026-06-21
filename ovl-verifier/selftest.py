#!/usr/bin/env python3
"""Self-test: confirm ovl_verifier reproduces every published golden vector.

Stdlib only — no SAGE code, no network. Run it anywhere:

    python3 selftest.py

Exit 0 = the verifier in this directory reproduces all published vectors (verdict + content_hash).
This is the same check the issuer runs in CI against the LIVE attestation engine, so a green
self-test here means this published verifier matches what the issuer actually computes.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ovl_verifier as V

vectors = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden_vectors.json")))
fails = 0
for g in vectors:
    ok, h = V.verify(g)
    verdict_ok = V.evaluate(g["claim"], g["value_def"], g["anchor_obtained"]) == g["verdict"]
    if ok and h == g["content_hash"] and verdict_ok:
        print(f"  [OK]   {g['name']:18s} {g['verdict']['valued']}/{g['verdict']['independence']}  {h[:16]}...")
    else:
        fails += 1
        print(f"  [FAIL] {g['name']:18s} recomputed {h} != {g['content_hash']}")

print(f"\n{len(vectors)} vectors, {len(vectors) - fails} reproduced, {fails} failures")
sys.exit(0 if fails == 0 else 1)
