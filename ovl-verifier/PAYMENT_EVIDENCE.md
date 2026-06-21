# Correlating an OVL receipt to its payment

A paid OVL receipt is issued after an **x402** micropayment. Where is the payment reference?

## The receipt body does NOT carry a payment reference
The `/tools/attest` door returns the attestation verbatim — `content_hash`, `verdict`, `mandate`,
`ovl_ledger`, `signature`, etc. It contains **no** `tx_hash`, `payer`, or price field.

## The HTTP response does NOT carry `X-PAYMENT-RESPONSE`
Despite the x402 convention, the live door emits **no** `X-PAYMENT-RESPONSE` settlement header. Do not
rely on it. (Response headers are only `date, server, x-request-id, cache-control, content-length,
content-type`.)

## Where the payment evidence actually lives
The settlement is correlated through three records that share the **on-chain settlement tx hash**:

1. **Issuer-side payment log** — `o2_economy.db` table `x402_payments`: `tx_hash`, `payer_wallet`,
   `amount_usd` (0.20), `tool` (`/tools/attest`), `success`, `timestamp`.
2. **Issuer-side mint** — `o2_economy.db` table `o2_transactions`: `reference_id == tx_hash`,
   `network` (e.g. `eip155:84532` = Base Sepolia testnet), `livemode` (0 = testnet).
3. **On-chain** — the USDC `transferWithAuthorization` settlement on the stated chain. Verify it
   yourself with any RPC:
   ```bash
   TX=0x...   # the tx_hash from x402_payments / o2_transactions.reference_id
   curl -s -X POST https://sepolia.base.org -H 'Content-Type: application/json' \
     -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_getTransactionReceipt\",\"params\":[\"$TX\"]}"
   ```
   Confirm `status == 0x1`, the `to` is the USDC contract, and a `Transfer` log moves the expected
   value `from = payer` `to = payTo` (the receiver). For an **external-payer** attestation, assert
   `from != to` and value `> 0` — i.e. value crossed between two distinct wallets.

## What this proves — and does not
Payment correlation shows a settled testnet payment is tied to this issuance. It does **not** by
itself prove external/arms-length revenue (a self-payment where `payer == payTo` moves net-zero
value), nor mainnet, nor real funds (testnet USDC is worthless). The receipt's own guarantees
(re-derivable `content_hash`, issuer-signature origin) are independent of the payment — see
`README.md` and `SPEC.md`.
