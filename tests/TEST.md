# v2 validation plan

- Unit: original safe core method/path/params contracts, structured output, HTTP-200 failures, credential precedence and origin isolation, 64-bit ids, bounded cursor/page pagination, atomic no-clobber export.
- Loopback integration: actual requests through local mock HTTP service; no real business endpoint or credential. Personal/team discovery and cursor forwarding; self checkout confirmation and pre-request journal; read-only request recovery; self redemption; loopback PKCE state and verifier delivery.
- Release: exact raw-byte Ed25519 verification, invalid/tampered manifests and wheel rejection; install-source refusal; manager success/failure restoration; opt-in and automation bypass.
- Artifact: build the current wheel, install into a new environment, call that environment's module and both console entrypoints; never use a PATH-resolved older CLI.
- CI: Python 3.10/3.12 on Linux/macOS/Windows. Real OS manager recovery, actual gateways/payment and protected release remain separate acceptance.
